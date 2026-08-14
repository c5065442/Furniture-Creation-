from rest_framework import serializers

from .models import ManufacturingList, ManufacturingListItem


class ManufacturingListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManufacturingListItem
        fields = [
            "id", "manufacturing_list", "order_item", "product_label", "quantity",
            "finish_name", "colour", "width_mm", "height_mm", "depth_mm", "status",
        ]


class ManufacturingListSerializer(serializers.ModelSerializer):
    items = ManufacturingListItemSerializer(many=True, read_only=True)
    run_date = serializers.DateField(source="delivery_run.run_date", read_only=True)
    van_name = serializers.CharField(source="delivery_run.van.name", read_only=True)

    class Meta:
        model = ManufacturingList
        fields = ["id", "delivery_run", "run_date", "van_name", "source_type", "status", "items"]
