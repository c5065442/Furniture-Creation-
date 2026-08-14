from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.products.models import FinishOption


class Customer(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="customer_profile"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class DeliveryAddress(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True, related_name="addresses")
    label = models.CharField(max_length=60, blank=True)  # e.g. "Home", "Workshop"
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    county = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=12)
    country = models.CharField(max_length=100, default="United Kingdom")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geocoded_at = models.DateTimeField(null=True, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "delivery addresses"

    def __str__(self):
        return f"{self.line1}, {self.postcode}"

    @property
    def is_geocoded(self):
        return self.latitude is not None and self.longitude is not None


class CustomerPreference(TimeStampedModel):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="preference")
    preferred_finish = models.ForeignKey(FinishOption, on_delete=models.SET_NULL, null=True, blank=True)
    preferred_colour = models.CharField(max_length=60, blank=True)
    delivery_notes = models.TextField(blank=True)  # e.g. "prefers morning delivery"
