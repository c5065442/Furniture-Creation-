from django.contrib import admin

from .models import FinishOption, Product, ProductCategory, ProductImage, ProductVariant


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "base_price", "is_bespoke_only", "is_active")
    list_filter = ("category", "is_bespoke_only", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline, ProductImageInline]


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(FinishOption)
class FinishOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "width_mm", "height_mm", "depth_mm", "finish", "colour", "price", "is_active")
    list_filter = ("finish", "is_active")
    search_fields = ("sku",)
