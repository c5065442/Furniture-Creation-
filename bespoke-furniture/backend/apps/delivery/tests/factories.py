"""Small test-data builders shared across delivery and manufacturing tests."""

from apps.customers.models import Customer, DeliveryAddress
from apps.delivery.models import DeliveryRun, RouteStop, Van
from apps.orders.models import Order, OrderItem


def build_delivery_run_with_stops(n_stops=2, run_status=DeliveryRun.Status.DRAFT):
    depot_customer = Customer.objects.create(first_name="Depot", last_name="HQ", email="depot-test@bfc.local")
    depot_address = DeliveryAddress.objects.create(
        customer=depot_customer, line1="Unit 1", city="Sheffield", postcode="S9 1AT",
        latitude=53.40, longitude=-1.42,
    )
    van = Van.objects.create(
        registration="TEST01", name="Test Van", max_weight_kg=1000,
        load_length_mm=4000, load_width_mm=1800, load_height_mm=1800, home_depot=depot_address,
    )
    run = DeliveryRun.objects.create(run_date="2026-09-01", van=van, status=run_status)

    stops = []
    for i in range(n_stops):
        customer = Customer.objects.create(first_name=f"Cust{i}", last_name="Test", email=f"cust{i}-test@bfc.local")
        address = DeliveryAddress.objects.create(
            customer=customer, line1=f"{i} Test St", city="Sheffield", postcode="S10 2TN",
            latitude=53.38 + i / 1000, longitude=-1.49,
        )
        order = Order.objects.create(delivery_address=address, customer=customer, status=Order.Status.READY_FOR_DELIVERY)
        OrderItem.objects.create(
            order=order, quantity=1, unit_price=100, width_mm=500, height_mm=500, depth_mm=500,
            weight_kg=10, requires_van=True,
        )
        stop = RouteStop.objects.create(
            delivery_run=run, order=order, sequence=i + 1, load_position=n_stops - i,
        )
        stops.append(stop)

    return run, stops
