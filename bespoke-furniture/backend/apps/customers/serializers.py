from rest_framework import serializers

from .models import Customer, CustomerPreference, DeliveryAddress


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = [
            "id", "customer", "label", "line1", "line2", "city", "county",
            "postcode", "country", "latitude", "longitude", "is_default",
        ]
        read_only_fields = ["latitude", "longitude"]


class CustomerPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerPreference
        fields = ["id", "customer", "preferred_finish", "preferred_colour", "delivery_notes"]


class CustomerSerializer(serializers.ModelSerializer):
    addresses = DeliveryAddressSerializer(many=True, read_only=True)
    preference = CustomerPreferenceSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "user", "first_name", "last_name", "email", "phone", "addresses", "preference"]
