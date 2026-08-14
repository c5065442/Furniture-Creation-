from django.contrib import admin

from .models import ManufacturingList, ManufacturingListItem


class ManufacturingListItemInline(admin.TabularInline):
    model = ManufacturingListItem
    extra = 0


@admin.register(ManufacturingList)
class ManufacturingListAdmin(admin.ModelAdmin):
    list_display = ("id", "delivery_run", "source_type", "status", "created_at")
    list_filter = ("source_type", "status")
    inlines = [ManufacturingListItemInline]
