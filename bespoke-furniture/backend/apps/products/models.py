from django.db import models

from apps.core.models import TimeStampedModel


class ProductCategory(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "product categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class FinishOption(TimeStampedModel):
    name = models.CharField(max_length=120)  # e.g. "Oak Natural", "Walnut Stain"
    swatch_image = models.ImageField(upload_to="finish_swatches/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_bespoke_only = models.BooleanField(default=False)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductVariant(TimeStampedModel):
    """A concrete purchasable SKU: a specific size/finish/colour combination of a Product."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True)
    width_mm = models.PositiveIntegerField()
    height_mm = models.PositiveIntegerField()
    depth_mm = models.PositiveIntegerField()
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2)
    finish = models.ForeignKey(FinishOption, on_delete=models.SET_NULL, null=True, blank=True, related_name="variants")
    colour = models.CharField(max_length=60, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("product", "width_mm", "height_mm", "depth_mm", "finish", "colour")
        ordering = ["sku"]

    def __str__(self):
        return self.sku


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="product_images/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "id"]
