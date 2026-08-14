from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.customers.models import DeliveryAddress
from apps.orders.models import Order


class Van(TimeStampedModel):
    registration = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, blank=True)
    max_weight_kg = models.DecimalField(max_digits=7, decimal_places=2)
    load_length_mm = models.PositiveIntegerField()
    load_width_mm = models.PositiveIntegerField()
    load_height_mm = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    home_depot = models.ForeignKey(DeliveryAddress, on_delete=models.PROTECT, related_name="vans")

    def __str__(self):
        return self.name or self.registration

    @property
    def load_volume_m3(self) -> float:
        return (self.load_length_mm * self.load_width_mm * self.load_height_mm) / 1_000_000_000


class DeliveryRun(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PLANNED = "PLANNED", "Planned"
        LOCKED = "LOCKED", "Locked"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    run_date = models.DateField()
    van = models.ForeignKey(Van, on_delete=models.PROTECT, related_name="runs")
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_runs",
        limit_choices_to={"role": "DRIVER"},
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    total_distance_km = models.FloatField(null=True, blank=True)
    total_duration_min = models.FloatField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-run_date"]

    def __str__(self):
        return f"Run {self.run_date} ({self.van})"


class RouteStop(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ARRIVED = "ARRIVED", "Arrived"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Failed"

    delivery_run = models.ForeignKey(DeliveryRun, on_delete=models.CASCADE, related_name="stops")
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="route_stops")
    sequence = models.PositiveIntegerField()  # 1 = delivered first
    load_position = models.PositiveIntegerField()  # 1 = loaded first (=> delivered last)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    eta = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    driver_notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("delivery_run", "order")
        ordering = ["delivery_run", "sequence"]

    def __str__(self):
        return f"{self.delivery_run} stop {self.sequence}: {self.order.order_number}"


class ParcelShipment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="parcel_shipment")
    carrier = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    shipped_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Parcel for {self.order.order_number}"


class DeliverySettings(TimeStampedModel):
    """Staff-editable singleton (pk=1) holding tunable delivery thresholds."""

    parcel_max_dimension_mm = models.PositiveIntegerField(default=600)
    parcel_max_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, default=25)
    van_load_safety_factor = models.FloatField(default=0.9)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls) -> "DeliverySettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Delivery settings"
