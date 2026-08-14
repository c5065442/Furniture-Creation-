"""
Seeds realistic demo/test data: product catalog, vans, customers spread
across several UK postcode districts, and a mix of pending orders (some
old/large enough to trigger a predictive-batching "schedule now" suggestion,
others fresh and small to demonstrate "wait"). Safe to run repeatedly
(get_or_create everywhere) and used both for live demos and as a basis for
manual testing across phases.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.models import Customer, DeliveryAddress
from apps.delivery.models import DeliveryRun, RouteStop, Van
from apps.delivery.services.classification import classify_order
from apps.orders.models import Order, OrderItem
from apps.products.models import FinishOption, Product, ProductCategory, ProductVariant

REGIONS = [
    # (postcode, city, lat, lng)
    ("S10 2TN", "Sheffield", 53.376, -1.494),
    ("S10 3AB", "Sheffield", 53.378, -1.492),
    ("M1 1AE", "Manchester", 53.480, -2.240),
    ("LS1 1AA", "Leeds", 53.797, -1.549),
]

DEPOT = ("S9 1AT", "Sheffield", 53.400, -1.420)


class Command(BaseCommand):
    help = "Seed realistic demo data for products, vans, customers, and orders."

    def handle(self, *args, **options):
        self.stdout.write("Seeding admin/staff/driver users…")
        self._seed_users()

        self.stdout.write("Seeding product catalog…")
        variant = self._seed_catalog()

        self.stdout.write("Seeding van + depot…")
        van = self._seed_van()

        self.stdout.write("Seeding customers and orders…")
        self._seed_orders(variant)

        self.stdout.write("Seeding one past (completed) delivery run for cadence history…")
        self._seed_past_run(van)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))

    def _seed_users(self):
        if not User.objects.filter(username="driver1").exists():
            driver = User.objects.create_user(username="driver1", password="DevDriver123!", role=User.Role.DRIVER)
            driver.first_name = "Dave"
            driver.last_name = "Driver"
            driver.save()

    def _seed_catalog(self) -> ProductVariant:
        category, _ = ProductCategory.objects.get_or_create(name="Shelving", slug="shelving")
        finish, _ = FinishOption.objects.get_or_create(name="Oak Natural")
        product, _ = Product.objects.get_or_create(
            category=category, name="Pine Shelf", slug="pine-shelf", defaults={"base_price": 45}
        )
        variant, _ = ProductVariant.objects.get_or_create(
            product=product,
            sku="BFC-SEED-0001",
            defaults=dict(width_mm=900, height_mm=200, depth_mm=250, weight_kg=4.5, finish=finish, colour="Natural", price=49.99),
        )

        dresser_category, _ = ProductCategory.objects.get_or_create(name="Dressers", slug="dressers")
        dresser, _ = Product.objects.get_or_create(
            category=dresser_category, name="Oak Dresser", slug="oak-dresser",
            defaults={"base_price": 1200, "is_bespoke_only": True},
        )
        ProductVariant.objects.get_or_create(
            product=dresser, sku="BFC-SEED-0002",
            defaults=dict(width_mm=3000, height_mm=1200, depth_mm=500, weight_kg=80, finish=finish, colour="Oak", price=1450),
        )
        return variant

    def _seed_van(self) -> Van:
        postcode, city, lat, lng = DEPOT
        depot_customer, _ = Customer.objects.get_or_create(
            email="depot@bfc-demo.local", defaults=dict(first_name="Depot", last_name="HQ")
        )
        depot_address, _ = DeliveryAddress.objects.get_or_create(
            customer=depot_customer, line1="Unit 1 Industrial Estate", city=city, postcode=postcode,
            defaults=dict(latitude=lat, longitude=lng, geocoded_at=timezone.now()),
        )
        van, _ = Van.objects.get_or_create(
            registration="BFC-DEMO-01",
            defaults=dict(
                name="Demo Van 1", max_weight_kg=1000, load_length_mm=4000, load_width_mm=1800,
                load_height_mm=1800, home_depot=depot_address,
            ),
        )
        return van

    def _seed_orders(self, variant: ProductVariant):
        # Region 0 (S10): several old, large bespoke orders -> should trigger
        # a "schedule now" predictive-batching suggestion.
        for i in range(3):
            self._make_order(REGIONS[0], bespoke=True, days_old=12 + i, big=True)

        # Region 2 (M1): one fresh, small catalog order -> should suggest "wait".
        self._make_order(REGIONS[2], bespoke=False, days_old=1, variant=variant)

        # Region 3 (LS1): a mid-size fresh bespoke order, below thresholds.
        self._make_order(REGIONS[3], bespoke=True, days_old=2, big=False)

    def _make_order(self, region, bespoke, days_old, big=False, variant=None):
        postcode, city, lat, lng = region
        customer, _ = Customer.objects.get_or_create(
            email=f"demo-{postcode.replace(' ', '')}-{days_old}-{big}@bfc-demo.local",
            defaults=dict(first_name="Demo", last_name="Customer", phone="07700900000"),
        )
        address = DeliveryAddress.objects.create(
            customer=customer, line1="1 Demo Street", city=city, postcode=postcode,
            latitude=lat, longitude=lng, geocoded_at=timezone.now(),
        )
        order = Order.objects.create(delivery_address=address, customer=customer, is_bespoke=bespoke)

        if variant:
            OrderItem.objects.create(
                order=order, product_variant=variant, quantity=1, unit_price=variant.price,
                finish_name=variant.finish.name if variant.finish else "", colour=variant.colour,
                width_mm=variant.width_mm, height_mm=variant.height_mm, depth_mm=variant.depth_mm,
                weight_kg=variant.weight_kg,
            )
        else:
            width = 3800 if big else 900
            OrderItem.objects.create(
                order=order, quantity=1, unit_price=1200 if big else 300,
                width_mm=width, height_mm=1700 if big else 700, depth_mm=1700 if big else 500,
                weight_kg=90 if big else 20,
            )

        order.status = Order.Status.CONFIRMED
        order.total_price = sum(item.unit_price * item.quantity for item in order.items.all())
        order.save(update_fields=["status", "total_price"])
        classify_order(order)
        order.status = Order.Status.CONFIRMED
        order.placed_at = timezone.now() - timedelta(days=days_old)
        order.save(update_fields=["status", "placed_at"])
        return order

    def _seed_past_run(self, van: Van):
        if DeliveryRun.objects.filter(van=van, status=DeliveryRun.Status.COMPLETED).exists():
            return
        postcode, city, lat, lng = REGIONS[0]
        customer, _ = Customer.objects.get_or_create(
            email="demo-past-run@bfc-demo.local", defaults=dict(first_name="Past", last_name="Order")
        )
        address = DeliveryAddress.objects.create(
            customer=customer, line1="9 Past St", city=city, postcode=postcode, latitude=lat, longitude=lng,
            geocoded_at=timezone.now(),
        )
        order = Order.objects.create(
            delivery_address=address, customer=customer, is_bespoke=True,
            status=Order.Status.DELIVERED, delivery_method=Order.DeliveryMethod.VAN,
        )
        OrderItem.objects.create(
            order=order, quantity=1, unit_price=500, width_mm=2000, height_mm=800, depth_mm=600,
            weight_kg=50, requires_van=True,
        )
        run = DeliveryRun.objects.create(
            run_date=(timezone.now() - timedelta(days=21)).date(), van=van, status=DeliveryRun.Status.COMPLETED,
        )
        RouteStop.objects.create(delivery_run=run, order=order, sequence=1, load_position=1, status=RouteStop.Status.DELIVERED)
