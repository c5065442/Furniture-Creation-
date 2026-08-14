from rest_framework import serializers

from .models import CustomAttachment, Order, OrderItem


class CustomAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomAttachment
        fields = ["id", "order_item", "file", "original_filename", "content_type", "notes"]
        read_only_fields = ["original_filename", "content_type"]


class OrderItemSerializer(serializers.ModelSerializer):
    attachments = CustomAttachmentSerializer(many=True, read_only=True)
    product_label = serializers.CharField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id", "order", "product_variant", "product_label", "custom_description", "quantity",
            "unit_price", "finish_name", "colour", "width_mm", "height_mm", "depth_mm",
            "weight_kg", "requires_van", "attachments",
        ]
        read_only_fields = ["requires_van"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "customer", "customer_name", "delivery_address", "status",
            "delivery_method", "payment_method", "is_bespoke", "placed_at", "total_price", "notes", "items",
        ]
        read_only_fields = ["order_number", "placed_at", "delivery_method", "total_price"]

    def get_customer_name(self, obj):
        return str(obj.customer) if obj.customer else "Guest"


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["status"]
