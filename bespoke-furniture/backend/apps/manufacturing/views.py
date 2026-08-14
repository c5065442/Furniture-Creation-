from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsStaff

from .models import ManufacturingList, ManufacturingListItem
from .serializers import ManufacturingListItemSerializer, ManufacturingListSerializer


class ManufacturingListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ManufacturingList.objects.select_related("delivery_run__van").prefetch_related("items")
    serializer_class = ManufacturingListSerializer
    permission_classes = [IsStaff]
    filterset_fields = ["delivery_run"]

    @action(detail=True, methods=["patch"], url_path=r"items/(?P<item_id>\d+)")
    def update_item(self, request, pk=None, item_id=None):
        item = ManufacturingListItem.objects.filter(pk=item_id, manufacturing_list_id=pk).first()
        if not item:
            return Response({"detail": "Not found."}, status=404)
        serializer = ManufacturingListItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
