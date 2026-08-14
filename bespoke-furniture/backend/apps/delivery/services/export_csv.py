"""CSV export of a finalized delivery run, for drivers / warehouse loading sheets."""

import csv

from django.http import HttpResponse

from ..models import DeliveryRun

COLUMNS = [
    "Sequence", "Load position", "Order #", "Customer", "Address", "Postcode",
    "Item", "SKU", "Qty", "Dimensions (mm)", "Weight (kg)", "Has design attachment", "Phone",
]


def build_run_rows(run: DeliveryRun):
    rows = []
    for stop in run.stops.select_related("order__customer", "order__delivery_address").prefetch_related(
        "order__items__attachments", "order__items__product_variant"
    ):
        order = stop.order
        address = order.delivery_address
        for item in order.items.all():
            rows.append(
                [
                    stop.sequence,
                    stop.load_position,
                    order.order_number,
                    str(order.customer) if order.customer else "Guest",
                    f"{address.line1}, {address.city}",
                    address.postcode,
                    item.product_label,
                    item.product_variant.sku if item.product_variant else "BESPOKE",
                    item.quantity,
                    f"{item.width_mm}x{item.height_mm}x{item.depth_mm}",
                    item.weight_kg,
                    "Yes" if item.attachments.exists() else "No",
                    order.customer.phone if order.customer else "",
                ]
            )
    return rows


def export_run_csv(run: DeliveryRun) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="delivery_run_{run.pk}_{run.run_date}.csv"'
    writer = csv.writer(response)
    writer.writerow(COLUMNS)
    writer.writerows(build_run_rows(run))
    return response
