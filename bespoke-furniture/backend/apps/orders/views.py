from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.permissions import IsStaff

from .models import CustomAttachment, Order
from .order_creation import create_order
from .serializers import CustomAttachmentSerializer, OrderSerializer, OrderStatusUpdateSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related("customer", "delivery_address").prefetch_related("items__attachments")
    serializer_class = OrderSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "delivery_method", "is_bespoke"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        if self.action in {"list", "retrieve"}:
            return [permissions.IsAuthenticated()]
        return [IsStaff()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.role in {"ADMIN", "SALES", "WAREHOUSE"}:
            return qs
        customer = getattr(user, "customer_profile", None)
        return qs.filter(customer=customer) if customer else qs.none()

    def create(self, request, *args, **kwargs):
        order = create_order(request.data, request.FILES, request.user)
        return Response(OrderSerializer(order).data, status=201)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if order.status == Order.Status.CONFIRMED and order.delivery_method is None:
            from apps.delivery.services.classification import classify_order

            classify_order(order)
            order.refresh_from_db()

        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="attachments")
    def add_attachment(self, request, pk=None):
        order = self.get_object()
        item_id = request.data.get("order_item")
        item = order.items.filter(pk=item_id).first()
        if not item:
            return Response({"detail": "order_item not found on this order."}, status=400)
        file_obj = request.FILES.get("file")
        attachment = CustomAttachment.objects.create(
            order_item=item,
            file=file_obj,
            original_filename=getattr(file_obj, "name", ""),
            content_type=getattr(file_obj, "content_type", ""),
            notes=request.data.get("notes", ""),
        )
        return Response(CustomAttachmentSerializer(attachment).data, status=201)
