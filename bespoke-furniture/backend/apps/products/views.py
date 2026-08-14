from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsStaffOrReadOnly

from .models import FinishOption, Product, ProductCategory, ProductVariant
from .serializers import (
    FinishOptionSerializer,
    ProductCategorySerializer,
    ProductListSerializer,
    ProductSerializer,
    ProductVariantSerializer,
)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [IsStaffOrReadOnly]


class FinishOptionViewSet(viewsets.ModelViewSet):
    queryset = FinishOption.objects.all()
    serializer_class = FinishOptionSerializer
    permission_classes = [IsStaffOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").prefetch_related("variants", "images")
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ["category", "is_bespoke_only", "is_active"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        return ProductSerializer

    def get_serializer_context(self):
        return {"request": self.request}

    @action(detail=True, methods=["get"])
    def variants(self, request, pk=None):
        product = self.get_object()
        serializer = ProductVariantSerializer(product.variants.all(), many=True)
        return Response(serializer.data)


class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset = ProductVariant.objects.select_related("product", "finish")
    serializer_class = ProductVariantSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ["product", "is_active"]
