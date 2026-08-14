from django.contrib import admin

from .models import DeliveryRun, DeliverySettings, ParcelShipment, RouteStop, Van


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 0


@admin.register(Van)
class VanAdmin(admin.ModelAdmin):
    list_display = ("name", "registration", "max_weight_kg", "is_active")


@admin.register(DeliveryRun)
class DeliveryRunAdmin(admin.ModelAdmin):
    list_display = ("run_date", "van", "driver", "status", "total_duration_min")
    list_filter = ("status", "van")
    inlines = [RouteStopInline]


@admin.register(ParcelShipment)
class ParcelShipmentAdmin(admin.ModelAdmin):
    list_display = ("order", "carrier", "tracking_number", "status")


@admin.register(DeliverySettings)
class DeliverySettingsAdmin(admin.ModelAdmin):
    list_display = ("parcel_max_dimension_mm", "parcel_max_weight_kg", "van_load_safety_factor")

    def has_add_permission(self, request):
        return not DeliverySettings.objects.exists()
