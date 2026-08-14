from rest_framework import serializers

from apps.orders.serializers import OrderSerializer

from .models import DeliveryRun, DeliverySettings, RouteStop, Van


class VanSerializer(serializers.ModelSerializer):
    load_volume_m3 = serializers.FloatField(read_only=True)

    class Meta:
        model = Van
        fields = [
            "id", "registration", "name", "max_weight_kg", "load_length_mm",
            "load_width_mm", "load_height_mm", "load_volume_m3", "is_active", "home_depot",
        ]


class RouteStopSerializer(serializers.ModelSerializer):
    order_detail = OrderSerializer(source="order", read_only=True)

    class Meta:
        model = RouteStop
        fields = [
            "id", "delivery_run", "order", "order_detail", "sequence", "load_position",
            "status", "eta", "delivered_at", "driver_notes",
        ]


class DeliveryRunSerializer(serializers.ModelSerializer):
    stops = RouteStopSerializer(many=True, read_only=True)
    van_name = serializers.CharField(source="van.name", read_only=True)
    driver_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryRun
        fields = [
            "id", "run_date", "van", "van_name", "driver", "driver_name", "status",
            "total_distance_km", "total_duration_min", "locked_at", "stops",
        ]
        read_only_fields = ["status", "locked_at", "total_distance_km", "total_duration_min"]

    def get_driver_name(self, obj):
        return obj.driver.get_full_name() or obj.driver.username if obj.driver else None


class DeliverySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverySettings
        fields = ["parcel_max_dimension_mm", "parcel_max_weight_kg", "van_load_safety_factor"]


class StopReorderSerializer(serializers.Serializer):
    stop_id = serializers.IntegerField()
    sequence = serializers.IntegerField(min_value=1)


class PlanRunRequestSerializer(serializers.Serializer):
    run_date = serializers.DateField()
    van_ids = serializers.ListField(child=serializers.IntegerField(), required=False)


class RegionSuggestionSerializer(serializers.Serializer):
    region = serializers.CharField()
    pending_order_count = serializers.IntegerField()
    pending_volume_m3 = serializers.FloatField()
    pending_weight_kg = serializers.FloatField()
    oldest_pending_order_days = serializers.IntegerField()
    suggested_action = serializers.CharField()
    suggested_date = serializers.DateField(allow_null=True)
    rationale = serializers.CharField()
