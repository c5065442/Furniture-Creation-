import pytest

from apps.customers.models import Customer, DeliveryAddress
from apps.delivery.models import DeliverySettings
from apps.delivery.services.classification import classify_order
from apps.orders.models import Order, OrderItem

pytestmark = pytest.mark.django_db


@pytest.fixture
def address():
    customer = Customer.objects.create(first_name="Jane", last_name="Doe", email="jane@example.com")
    return DeliveryAddress.objects.create(customer=customer, line1="1 High St", city="Sheffield", postcode="S1 2AB")


def make_order(address, is_bespoke=False):
    return Order.objects.create(delivery_address=address, is_bespoke=is_bespoke)


def make_item(order, **overrides):
    defaults = dict(
        quantity=1, unit_price=10, width_mm=100, height_mm=100, depth_mm=100, weight_kg=1,
    )
    defaults.update(overrides)
    return OrderItem.objects.create(order=order, **defaults)


class TestClassifyOrder:
    def test_small_light_item_goes_by_parcel(self, address):
        order = make_order(address)
        make_item(order, width_mm=100, height_mm=100, depth_mm=100, weight_kg=1)

        method = classify_order(order)

        assert method == Order.DeliveryMethod.PARCEL
        assert order.items.get().requires_van is False

    def test_oversized_item_requires_van(self, address):
        settings_obj = DeliverySettings.load()
        order = make_order(address)
        make_item(order, width_mm=settings_obj.parcel_max_dimension_mm + 1, height_mm=100, depth_mm=100, weight_kg=1)

        method = classify_order(order)

        assert method == Order.DeliveryMethod.VAN
        assert order.items.get().requires_van is True

    def test_exactly_at_threshold_does_not_require_van(self, address):
        settings_obj = DeliverySettings.load()
        order = make_order(address)
        make_item(
            order,
            width_mm=settings_obj.parcel_max_dimension_mm,
            height_mm=100,
            depth_mm=100,
            weight_kg=float(settings_obj.parcel_max_weight_kg),
        )

        method = classify_order(order)

        assert method == Order.DeliveryMethod.PARCEL

    def test_overweight_item_requires_van(self, address):
        settings_obj = DeliverySettings.load()
        order = make_order(address)
        make_item(order, weight_kg=float(settings_obj.parcel_max_weight_kg) + 1)

        method = classify_order(order)

        assert method == Order.DeliveryMethod.VAN

    def test_bespoke_order_always_requires_van_even_if_small(self, address):
        order = make_order(address, is_bespoke=True)
        make_item(order, width_mm=50, height_mm=50, depth_mm=50, weight_kg=0.5)

        method = classify_order(order)

        assert method == Order.DeliveryMethod.VAN
        assert order.items.get().requires_van is True

    def test_mixed_order_is_van_if_any_single_item_requires_it(self, address):
        settings_obj = DeliverySettings.load()
        order = make_order(address)
        make_item(order, width_mm=100, height_mm=100, depth_mm=100, weight_kg=1)  # parcel-eligible
        make_item(order, width_mm=settings_obj.parcel_max_dimension_mm + 100, height_mm=100, depth_mm=100, weight_kg=1)

        method = classify_order(order)

        assert method == Order.DeliveryMethod.VAN
        items = list(order.items.all())
        assert sum(1 for i in items if i.requires_van) == 1
        assert sum(1 for i in items if not i.requires_van) == 1
