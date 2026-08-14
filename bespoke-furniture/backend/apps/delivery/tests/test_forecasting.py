from datetime import timedelta

import pytest
from django.utils import timezone

from apps.customers.models import Customer, DeliveryAddress
from apps.delivery.models import Van
from apps.delivery.services.classification import classify_order
from apps.delivery.services.forecasting import suggest_delivery_runs
from apps.orders.models import Order, OrderItem

pytestmark = pytest.mark.django_db


def make_van():
    depot_customer = Customer.objects.create(first_name="Depot", last_name="HQ", email="depot-fc@bfc.local")
    depot_address = DeliveryAddress.objects.create(
        customer=depot_customer, line1="Unit 1", city="Sheffield", postcode="S9 1AT",
        latitude=53.40, longitude=-1.42,
    )
    return Van.objects.create(
        registration="FC01", name="Forecast Van", max_weight_kg=1000,
        load_length_mm=4000, load_width_mm=1800, load_height_mm=1800, home_depot=depot_address,
    )


def make_pending_van_order(postcode, days_old=1, big=False):
    customer = Customer.objects.create(
        first_name="C", last_name="Test", email=f"fc-{postcode}-{days_old}-{big}@bfc.local"
    )
    address = DeliveryAddress.objects.create(
        customer=customer, line1="1 St", city="Sheffield", postcode=postcode, latitude=53.38, longitude=-1.49,
    )
    order = Order.objects.create(delivery_address=address, is_bespoke=True, status=Order.Status.CONFIRMED)
    width = 3800 if big else 500
    OrderItem.objects.create(
        order=order, quantity=1, unit_price=100, width_mm=width, height_mm=1700, depth_mm=1700, weight_kg=10,
    )
    classify_order(order)
    order.status = Order.Status.CONFIRMED
    order.placed_at = timezone.now() - timedelta(days=days_old)
    order.save(update_fields=["status", "placed_at"])
    return order


class TestSuggestDeliveryRuns:
    def test_no_pending_orders_produces_no_suggestions(self):
        make_van()
        assert suggest_delivery_runs() == []

    def test_old_pending_order_triggers_schedule_now(self, settings):
        settings.DELIVERY_SCHEDULE_SLA_DAYS = 10
        make_van()
        make_pending_van_order("S10 2TN", days_old=15)

        suggestions = suggest_delivery_runs()

        assert len(suggestions) == 1
        assert suggestions[0].region == "S10"
        assert suggestions[0].suggested_action == "SCHEDULE_NOW"

    def test_recent_small_pending_order_suggests_wait(self, settings):
        settings.DELIVERY_SCHEDULE_SLA_DAYS = 10
        make_van()
        make_pending_van_order("M1 1AE", days_old=1, big=False)

        suggestions = suggest_delivery_runs()

        assert len(suggestions) == 1
        assert suggestions[0].suggested_action == "WAIT"

    def test_near_capacity_pending_load_triggers_schedule_now(self, settings):
        settings.DELIVERY_CAPACITY_THRESHOLD_FRACTION = 0.5
        settings.DELIVERY_SCHEDULE_SLA_DAYS = 100
        make_van()
        make_pending_van_order("LS1 1AA", days_old=1, big=True)

        suggestions = suggest_delivery_runs()

        assert len(suggestions) == 1
        assert suggestions[0].suggested_action == "SCHEDULE_NOW"

    def test_regions_are_grouped_independently(self, settings):
        settings.DELIVERY_SCHEDULE_SLA_DAYS = 10
        make_van()
        make_pending_van_order("S10 2TN", days_old=15)  # triggers SCHEDULE_NOW
        make_pending_van_order("M1 1AE", days_old=1)  # WAIT

        suggestions = {s.region: s.suggested_action for s in suggest_delivery_runs()}

        assert suggestions["S10"] == "SCHEDULE_NOW"
        assert suggestions["M1"] == "WAIT"
