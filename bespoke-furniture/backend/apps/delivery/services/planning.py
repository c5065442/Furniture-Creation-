"""
Orchestrates the delivery-run planning pipeline:
  candidate pool -> geocode -> cluster -> capacity-select per van -> route -> persist as DRAFT runs.

Called from DeliveryRunViewSet.plan(); kept out of the view so it stays a
plain, testable function.
"""

from django.db import transaction

from apps.orders.models import Order

from ..models import DeliveryRun, DeliverySettings, RouteStop, Van
from .capacity import compute_order_load, select_orders_for_van
from .clustering import GeoPoint, cluster_points
from .geocoding import geocode_address
from .routing import RoutedStop, plan_route


def get_candidate_orders():
    """VAN-classified, ready-for-delivery, not already attached to a route stop."""
    return (
        Order.objects.filter(
            delivery_method=Order.DeliveryMethod.VAN,
            status=Order.Status.READY_FOR_DELIVERY,
        )
        .exclude(route_stops__isnull=False)
        .select_related("delivery_address")
        .prefetch_related("items")
    )


@transaction.atomic
def plan_delivery_runs(run_date, van_ids: list[int] | None = None) -> list[DeliveryRun]:
    """
    Builds one DRAFT DeliveryRun per available van for run_date, assigning
    candidate orders via clustering + capacity + routing. Returns the created
    runs (possibly fewer than requested if there aren't enough candidates).
    """
    vans = list(Van.objects.filter(is_active=True, pk__in=van_ids) if van_ids else Van.objects.filter(is_active=True))
    if not vans:
        return []

    settings_obj = DeliverySettings.load()
    candidates = list(get_candidate_orders())

    for order in candidates:
        geocode_address(order.delivery_address)

    points = [
        GeoPoint(
            order_id=order.id,
            postcode=order.delivery_address.postcode,
            latitude=float(order.delivery_address.latitude),
            longitude=float(order.delivery_address.longitude),
        )
        for order in candidates
        if order.delivery_address.is_geocoded
    ]

    clusters = cluster_points(points, target_cluster_count=len(vans))
    orders_by_id = {order.id: order for order in candidates}

    created_runs: list[DeliveryRun] = []
    remaining_clusters = list(clusters)

    for van in vans:
        if not remaining_clusters:
            break
        cluster = remaining_clusters.pop(0)
        loads = [compute_order_load(orders_by_id[oid]) for oid in cluster.order_ids]
        capacity_result = select_orders_for_van(loads, van, settings_obj.van_load_safety_factor)

        if not capacity_result.selected:
            continue

        depot = (float(van.home_depot.latitude), float(van.home_depot.longitude))
        stop_points = [
            (load.order_id, orders_by_id[load.order_id].delivery_address.latitude, orders_by_id[load.order_id].delivery_address.longitude)
            for load in capacity_result.selected
        ]
        stop_points = [(oid, float(lat), float(lng)) for oid, lat, lng in stop_points]

        route_result = plan_route(depot, stop_points)

        run = DeliveryRun.objects.create(
            run_date=run_date,
            van=van,
            status=DeliveryRun.Status.DRAFT,
            total_duration_min=route_result.total_duration_min,
        )
        _persist_stops(run, route_result.stops)
        created_runs.append(run)

    return created_runs


def _persist_stops(run: DeliveryRun, routed_stops: list[RoutedStop]) -> None:
    RouteStop.objects.bulk_create(
        [
            RouteStop(
                delivery_run=run,
                order_id=stop.order_id,
                sequence=stop.sequence,
                load_position=stop.load_position,
            )
            for stop in routed_stops
        ]
    )
