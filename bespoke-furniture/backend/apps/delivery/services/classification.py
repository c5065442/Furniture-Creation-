"""
Decide, per OrderItem, whether it must go by van (large/heavy/bespoke) or
can go via national parcel service (small). Computed once at order
confirmation and stored on the model, so later threshold tuning in
DeliverySettings never retroactively changes an already-confirmed order.
"""

from apps.orders.models import Order, OrderItem

from ..models import DeliverySettings


def item_requires_van(item: OrderItem, order: Order, settings_obj: DeliverySettings) -> bool:
    if order.is_bespoke:
        return True
    max_dimension = max(item.width_mm, item.height_mm, item.depth_mm)
    if max_dimension > settings_obj.parcel_max_dimension_mm:
        return True
    if item.weight_kg > settings_obj.parcel_max_weight_kg:
        return True
    return False


def classify_order(order: Order) -> str:
    """Sets requires_van on every item and delivery_method on the order. Returns the method."""
    settings_obj = DeliverySettings.load()
    items = list(order.items.all())

    for item in items:
        item.requires_van = item_requires_van(item, order, settings_obj)
    OrderItem.objects.bulk_update(items, ["requires_van"])

    method = Order.DeliveryMethod.VAN if any(i.requires_van for i in items) else Order.DeliveryMethod.PARCEL
    order.delivery_method = method
    order.save(update_fields=["delivery_method"])
    return method
