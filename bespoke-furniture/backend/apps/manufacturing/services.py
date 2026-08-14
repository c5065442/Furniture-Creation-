"""
Generates a ManufacturingList from a locked DeliveryRun: one ManufacturingListItem
per OrderItem on the run, snapshotting build-relevant fields so later catalog
or order edits never retroactively change what the workshop was told to build.
"""

from django.db import transaction

from apps.delivery.models import DeliveryRun

from .models import ManufacturingList, ManufacturingListItem


class ManufacturingListAlreadyExists(Exception):
    pass


@transaction.atomic
def generate_manufacturing_list(run: DeliveryRun, generated_by=None) -> ManufacturingList:
    if ManufacturingList.objects.filter(delivery_run=run).exists():
        raise ManufacturingListAlreadyExists(f"A manufacturing list already exists for run {run.pk}.")

    manufacturing_list = ManufacturingList.objects.create(
        delivery_run=run,
        source_type=ManufacturingList.SourceType.DELIVERY_RUN,
        generated_by=generated_by,
    )

    items = []
    for stop in run.stops.select_related("order").prefetch_related("order__items"):
        for order_item in stop.order.items.all():
            items.append(
                ManufacturingListItem(
                    manufacturing_list=manufacturing_list,
                    order_item=order_item,
                    product_label=order_item.product_label,
                    quantity=order_item.quantity,
                    finish_name=order_item.finish_name,
                    colour=order_item.colour,
                    width_mm=order_item.width_mm,
                    height_mm=order_item.height_mm,
                    depth_mm=order_item.depth_mm,
                )
            )
    ManufacturingListItem.objects.bulk_create(items)
    return manufacturing_list
