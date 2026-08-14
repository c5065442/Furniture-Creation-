from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.delivery.models import DeliveryRun
from apps.orders.models import OrderItem


class ManufacturingList(TimeStampedModel):
    class SourceType(models.TextChoices):
        DELIVERY_RUN = "DELIVERY_RUN", "Delivery run"
        PARCEL_BATCH = "PARCEL_BATCH", "Parcel batch"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETE = "COMPLETE", "Complete"

    delivery_run = models.OneToOneField(
        DeliveryRun, on_delete=models.CASCADE, null=True, blank=True, related_name="manufacturing_list"
    )
    source_type = models.CharField(max_length=15, choices=SourceType.choices, default=SourceType.DELIVERY_RUN)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)

    def __str__(self):
        return f"Manufacturing list #{self.pk} ({self.get_source_type_display()})"


class ManufacturingListItem(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CUTTING = "CUTTING", "Cutting"
        ASSEMBLY = "ASSEMBLY", "Assembly"
        FINISHING = "FINISHING", "Finishing"
        READY = "READY", "Ready"

    manufacturing_list = models.ForeignKey(ManufacturingList, on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name="manufacturing_items")

    # Snapshot fields for the build sheet, independent of later catalog/order edits.
    product_label = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    finish_name = models.CharField(max_length=120, blank=True)
    colour = models.CharField(max_length=60, blank=True)
    width_mm = models.PositiveIntegerField()
    height_mm = models.PositiveIntegerField()
    depth_mm = models.PositiveIntegerField()

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["manufacturing_list", "id"]

    def __str__(self):
        return f"{self.product_label} x{self.quantity}"
