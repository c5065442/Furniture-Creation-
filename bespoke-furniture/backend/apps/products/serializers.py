from rest_framework import serializers

from .models import FinishOption, Product, ProductCategory, ProductImage, ProductVariant


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "slug", "description"]


class FinishOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinishOption
        fields = ["id", "name", "swatch_image", "is_active"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary"]


class ProductVariantSerializer(serializers.ModelSerializer):
    finish_name = serializers.CharField(source="finish.name", read_only=True, default="")

    class Meta:
        model = ProductVariant
        fields = [
            "id", "product", "sku", "width_mm", "height_mm", "depth_mm", "weight_kg",
            "finish", "finish_name", "colour", "price", "is_active",
        ]


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "category", "category_name", "name", "slug", "description",
            "is_bespoke_only", "base_price", "is_active", "variants", "images",
        ]


class ProductListSerializer(serializers.ModelSerializer):
    """Lighter serializer for catalog listing pages (no nested variants/images)."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "category", "category_name", "name", "slug", "base_price", "is_bespoke_only", "primary_image"]

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()
        if not image:
            return None
        request = self.context.get("request")
        url = image.image.url
        return request.build_absolute_uri(url) if request else url
