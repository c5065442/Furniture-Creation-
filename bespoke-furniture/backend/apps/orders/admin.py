from django.contrib import admin

from .models import CustomAttachment, Order, OrderItem


class CustomAttachmentInline(admin.TabularInline):
    model = CustomAttachment
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "status", "delivery_method", "is_bespoke", "placed_at", "total_price")
    list_filter = ("status", "delivery_method", "is_bespoke")
    search_fields = ("order_number", "customer__first_name", "customer__last_name", "customer__email")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_label", "quantity", "requires_van")
    inlines = [CustomAttachmentInline]
