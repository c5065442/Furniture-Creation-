from django.contrib import admin

from .models import CustomerPreference, Customer, DeliveryAddress


class DeliveryAddressInline(admin.TabularInline):
    model = DeliveryAddress
    extra = 0


class CustomerPreferenceInline(admin.StackedInline):
    model = CustomerPreference
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone")
    search_fields = ("first_name", "last_name", "email", "phone")
    inlines = [DeliveryAddressInline, CustomerPreferenceInline]
