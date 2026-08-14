import uuid

from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.customers.models import Customer, DeliveryAddress
from apps.products.models import ProductVariant


def _generate_order_number():
    return f"BFC-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        IN_PRODUCTION = "IN_PRODUCTION", "In production"
        READY_FOR_DELIVERY = "READY_FOR_DELIVERY", "Ready for delivery"
        SCHEDULED = "SCHEDULED", "Scheduled"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for delivery"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    class DeliveryMethod(models.TextChoices):
        VAN = "VAN", "Van"
        PARCEL = "PARCEL", "Parcel"

    class PaymentMethod(models.TextChoices):
        CARD = "CARD", "Card"
        CASH_ON_DELIVERY = "CASH_ON_DELIVERY", "Cash on delivery"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"

    order_number = models.CharField(max_length=32, unique=True, default=_generate_order_number, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True, related_name="orders")
    delivery_address = models.ForeignKey(DeliveryAddress, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    delivery_method = models.CharField(max_length=10, choices=DeliveryMethod.choices, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CARD)
    is_bespoke = models.BooleanField(default=False)
    placed_at = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-placed_at"]

    def __str__(self):
        return self.order_number


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items"
    )
    custom_description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Snapshot fields: captured at order time so later catalog edits never
    # retroactively change what was actually ordered, manufactured, or delivered.
    finish_name = models.CharField(max_length=120, blank=True)
    colour = models.CharField(max_length=60, blank=True)
    width_mm = models.PositiveIntegerField()
    height_mm = models.PositiveIntegerField()
    depth_mm = models.PositiveIntegerField()
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2)

    requires_van = models.BooleanField(default=False)  # set by delivery.services.classification

    def __str__(self):
        return f"{self.order.order_number} - item {self.pk}"

    @property
    def product_label(self):
        if self.product_variant:
            return str(self.product_variant.product.name)
        return self.custom_description[:60] or "Bespoke item"


class CustomAttachment(TimeStampedModel):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="design_uploads/%Y/%m/")
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
