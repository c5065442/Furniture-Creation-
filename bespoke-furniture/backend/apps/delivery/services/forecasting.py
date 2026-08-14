"""
Predictive order batching: a simple, explainable heuristic (not ML) that
suggests when to schedule the next delivery run per geographic region.
Justified by the modest first-year order volume this system starts with --
a full time-series/ML forecasting pipeline would be overkill and unjustified
by the available data. Designed so it can be swapped for a real forecasting
model later without touching the rest of the delivery architecture.

Per postcode-district region:
  - pending order count / volume / weight (VAN orders confirmed or ready,
    not yet on a route stop)
  - oldest_pending_order_days: age of the longest-waiting pending order
  - historical_run_cadence_days: moving average of days between past runs
    that served this region

Suggests SCHEDULE_NOW if pending load crosses a capacity threshold or the
oldest order breaches an SLA; otherwise WAIT with a suggested_date based on
historical cadence.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

from apps.orders.models import Order

from ..models import DeliveryRun, Van
from .capacity import compute_order_load
from .clustering import postcode_district


@dataclass
class RegionSuggestion:
    region: str
    pending_order_count: int
    pending_volume_m3: float
    pending_weight_kg: float
    oldest_pending_order_days: int
    suggested_action: str  # "SCHEDULE_NOW" | "WAIT"
    suggested_date: date | None
    rationale: str


def _average_van_capacity() -> tuple[float, float]:
    vans = list(Van.objects.filter(is_active=True))
    if not vans:
        return 0.0, 0.0
    avg_volume = sum(v.load_volume_m3 for v in vans) / len(vans)
    avg_weight = sum(float(v.max_weight_kg) for v in vans) / len(vans)
    return avg_volume, avg_weight


def _pending_van_orders():
    return (
        Order.objects.filter(
            delivery_method=Order.DeliveryMethod.VAN,
            status__in=[Order.Status.CONFIRMED, Order.Status.READY_FOR_DELIVERY],
        )
        .exclude(route_stops__isnull=False)
        .select_related("delivery_address")
        .prefetch_related("items")
    )


def _historical_run_cadence_days(region: str) -> float | None:
    """Moving average of gaps (days) between past runs whose stops served this region."""
    run_dates = sorted(
        set(
            DeliveryRun.objects.filter(
                stops__order__delivery_address__postcode__istartswith=region
            ).values_list("run_date", flat=True)
        )
    )
    if len(run_dates) < 2:
        return None
    gaps = [(run_dates[i + 1] - run_dates[i]).days for i in range(len(run_dates) - 1)]
    return sum(gaps) / len(gaps)


def suggest_delivery_runs() -> list[RegionSuggestion]:
    today = timezone.now().date()
    sla_days = settings.DELIVERY_SCHEDULE_SLA_DAYS
    threshold_fraction = settings.DELIVERY_CAPACITY_THRESHOLD_FRACTION

    avg_volume, avg_weight = _average_van_capacity()
    volume_threshold = avg_volume * threshold_fraction
    weight_threshold = avg_weight * threshold_fraction

    orders = list(_pending_van_orders())
    regions: dict[str, list[Order]] = {}
    for order in orders:
        region = postcode_district(order.delivery_address.postcode)
        regions.setdefault(region, []).append(order)

    suggestions = []
    for region, region_orders in regions.items():
        loads = [compute_order_load(order) for order in region_orders]
        pending_volume = sum(load.volume_m3 for load in loads)
        pending_weight = sum(load.weight_kg for load in loads)
        oldest_days = max((today - order.placed_at.date()).days for order in region_orders)

        capacity_breached = bool(
            (avg_volume and pending_volume >= volume_threshold)
            or (avg_weight and pending_weight >= weight_threshold)
        )
        sla_breached = oldest_days >= sla_days

        cadence = _historical_run_cadence_days(region)

        if capacity_breached or sla_breached:
            reason = "pending load near van capacity" if capacity_breached else f"oldest order is {oldest_days} days old"
            suggestions.append(
                RegionSuggestion(
                    region=region,
                    pending_order_count=len(region_orders),
                    pending_volume_m3=pending_volume,
                    pending_weight_kg=pending_weight,
                    oldest_pending_order_days=oldest_days,
                    suggested_action="SCHEDULE_NOW",
                    suggested_date=today,
                    rationale=f"Schedule now: {reason}.",
                )
            )
        else:
            suggested_date = today + timedelta(days=round(cadence)) if cadence else None
            rationale = (
                f"Wait: pending load and order age are within normal range; "
                f"based on past cadence, expect to schedule around {suggested_date}."
                if suggested_date
                else "Wait: pending load and order age are within normal range; no historical cadence yet for this region."
            )
            suggestions.append(
                RegionSuggestion(
                    region=region,
                    pending_order_count=len(region_orders),
                    pending_volume_m3=pending_volume,
                    pending_weight_kg=pending_weight,
                    oldest_pending_order_days=oldest_days,
                    suggested_action="WAIT",
                    suggested_date=suggested_date,
                    rationale=rationale,
                )
            )

    return suggestions
