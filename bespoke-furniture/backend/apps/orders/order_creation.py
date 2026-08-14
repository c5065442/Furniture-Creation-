"""
Order placement: takes multipart/JSON request data and turns it into an
Order + OrderItems + CustomAttachments in one transaction.

Expected request shape (multipart or JSON):
    customer_email, customer_first_name, customer_last_name, customer_phone
    delivery_address_id  (int, use an existing address)      -- OR --
    delivery_address     (dict: line1, line2, city, county, postcode, country)
    notes
    items  (JSON-encoded string: list of dicts, see OrderItemInputSerializer)

Files (multipart only), one optional attachment per item by index:
    attachment_0, attachment_1, ...  -> matches items[0], items[1], ...
"""

import json

from django.db import transaction
from rest_framework import serializers

from apps.customers.models import Customer, DeliveryAddress
from apps.products.models import ProductVariant

from .models import CustomAttachment, Order, OrderItem


class OrderItemInputSerializer(serializers.Serializer):
    product_variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.filter(is_active=True), required=False, allow_null=True
    )
    custom_description = serializers.CharField(required=False, allow_blank=True, default="")
    quantity = serializers.IntegerField(min_value=1, default=1)
    finish_name = serializers.CharField(required=False, allow_blank=True, default="")
    colour = serializers.CharField(required=False, allow_blank=True, default="")
    width_mm = serializers.IntegerField(required=False, min_value=1)
    height_mm = serializers.IntegerField(required=False, min_value=1)
    depth_mm = serializers.IntegerField(required=False, min_value=1)
    weight_kg = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    def validate(self, attrs):
        variant = attrs.get("product_variant")
        if variant is None:
            missing = [f for f in ("width_mm", "height_mm", "depth_mm", "weight_kg", "unit_price") if f not in attrs]
            if missing:
                raise serializers.ValidationError(
                    f"Bespoke items with no product_variant must supply: {', '.join(missing)}"
                )
        return attrs


class DeliveryAddressInputSerializer(serializers.Serializer):
    label = serializers.CharField(required=False, allow_blank=True, default="")
    line1 = serializers.CharField()
    line2 = serializers.CharField(required=False, allow_blank=True, default="")
    city = serializers.CharField()
    county = serializers.CharField(required=False, allow_blank=True, default="")
    postcode = serializers.CharField()
    country = serializers.CharField(required=False, default="United Kingdom")


class OrderCreateInputSerializer(serializers.Serializer):
    customer_email = serializers.EmailField()
    customer_first_name = serializers.CharField()
    customer_last_name = serializers.CharField()
    customer_phone = serializers.CharField(required=False, allow_blank=True, default="")
    delivery_address_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryAddress.objects.all(), required=False, allow_null=True, source="delivery_address"
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices, default=Order.PaymentMethod.CARD)

    def validate(self, attrs):
        raw_items = self.initial_data.get("items")
        if not raw_items:
            raise serializers.ValidationError({"items": "At least one order item is required."})
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError({"items": "Must be valid JSON."}) from exc

        item_serializer = OrderItemInputSerializer(data=raw_items, many=True)
        item_serializer.is_valid(raise_exception=True)
        attrs["items"] = item_serializer.validated_data

        raw_address = self.initial_data.get("delivery_address")
        if not attrs.get("delivery_address") and not raw_address:
            raise serializers.ValidationError(
                {"delivery_address_id": "Provide an existing delivery_address_id or a new delivery_address."}
            )
        if not attrs.get("delivery_address"):
            if isinstance(raw_address, str):
                try:
                    raw_address = json.loads(raw_address)
                except json.JSONDecodeError as exc:
                    raise serializers.ValidationError({"delivery_address": "Must be valid JSON."}) from exc
            address_serializer = DeliveryAddressInputSerializer(data=raw_address)
            address_serializer.is_valid(raise_exception=True)
            attrs["new_address"] = address_serializer.validated_data
        return attrs


@transaction.atomic
def create_order(data, files, requesting_user=None):
    """data: request.data (dict-like); files: request.FILES. Returns the created Order."""
    serializer = OrderCreateInputSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    validated = serializer.validated_data

    is_authenticated = bool(requesting_user and requesting_user.is_authenticated)
    customer, _ = Customer.objects.get_or_create(
        email=validated["customer_email"],
        defaults={
            "first_name": validated["customer_first_name"],
            "last_name": validated["customer_last_name"],
            "phone": validated.get("customer_phone", ""),
            "user": requesting_user if is_authenticated else None,
        },
    )
    # Link a pre-existing guest Customer record to the now-authenticated
    # account, so their order history (including past guest orders under
    # this email) becomes visible once they register/log in.
    if is_authenticated and customer.user_id is None:
        customer.user = requesting_user
        customer.save(update_fields=["user"])

    delivery_address = validated.get("delivery_address")
    if delivery_address is None:
        delivery_address = DeliveryAddress.objects.create(customer=customer, **validated["new_address"])

    order = Order.objects.create(
        customer=customer,
        delivery_address=delivery_address,
        notes=validated.get("notes", ""),
        payment_method=validated["payment_method"],
    )

    total_price = 0
    is_bespoke = False
    for index, item_data in enumerate(validated["items"]):
        variant = item_data.get("product_variant")
        if variant:
            width_mm = item_data.get("width_mm", variant.width_mm)
            height_mm = item_data.get("height_mm", variant.height_mm)
            depth_mm = item_data.get("depth_mm", variant.depth_mm)
            weight_kg = item_data.get("weight_kg", variant.weight_kg)
            unit_price = item_data.get("unit_price", variant.price)
            finish_name = item_data.get("finish_name") or (variant.finish.name if variant.finish else "")
            colour = item_data.get("colour") or variant.colour
        else:
            is_bespoke = True
            width_mm = item_data["width_mm"]
            height_mm = item_data["height_mm"]
            depth_mm = item_data["depth_mm"]
            weight_kg = item_data["weight_kg"]
            unit_price = item_data["unit_price"]
            finish_name = item_data.get("finish_name", "")
            colour = item_data.get("colour", "")

        quantity = item_data.get("quantity", 1)
        order_item = OrderItem.objects.create(
            order=order,
            product_variant=variant,
            custom_description=item_data.get("custom_description", ""),
            quantity=quantity,
            unit_price=unit_price,
            finish_name=finish_name,
            colour=colour,
            width_mm=width_mm,
            height_mm=height_mm,
            depth_mm=depth_mm,
            weight_kg=weight_kg,
        )
        total_price += unit_price * quantity

        attachment_file = files.get(f"attachment_{index}") if files else None
        if attachment_file:
            CustomAttachment.objects.create(
                order_item=order_item,
                file=attachment_file,
                original_filename=attachment_file.name,
                content_type=getattr(attachment_file, "content_type", ""),
            )

    order.total_price = total_price
    order.is_bespoke = is_bespoke
    order.save(update_fields=["total_price", "is_bespoke"])
    return order
