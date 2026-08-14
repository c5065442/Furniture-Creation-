from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDriver, IsStaff

from .models import DeliveryRun, DeliverySettings, RouteStop, Van
from .serializers import (
    DeliveryRunSerializer,
    DeliverySettingsSerializer,
    PlanRunRequestSerializer,
    RegionSuggestionSerializer,
    RouteStopSerializer,
    StopReorderSerializer,
    VanSerializer,
)
from .services.export_csv import export_run_csv
from .services.export_pdf import export_run_pdf
from .services.forecasting import suggest_delivery_runs
from .services.planning import plan_delivery_runs


class VanViewSet(viewsets.ModelViewSet):
    queryset = Van.objects.select_related("home_depot")
    serializer_class = VanSerializer
    permission_classes = [IsStaff]


class DeliveryRunViewSet(viewsets.ModelViewSet):
    queryset = DeliveryRun.objects.select_related("van", "driver").prefetch_related("stops__order")
    serializer_class = DeliveryRunSerializer
    permission_classes = [IsStaff]
    filterset_fields = ["run_date", "status", "van"]

    @action(detail=False, methods=["post"])
    def plan(self, request):
        serializer = PlanRunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        runs = plan_delivery_runs(
            run_date=serializer.validated_data["run_date"],
            van_ids=serializer.validated_data.get("van_ids"),
        )
        return Response(DeliveryRunSerializer(runs, many=True).data, status=201)

    @action(detail=True, methods=["patch"], url_path="stops/reorder")
    def reorder_stops(self, request, pk=None):
        run = self.get_object()
        serializer = StopReorderSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        stops_by_id = {stop.id: stop for stop in run.stops.all()}
        n = len(stops_by_id)
        updated = []
        for entry in serializer.validated_data:
            stop = stops_by_id.get(entry["stop_id"])
            if not stop:
                continue
            stop.sequence = entry["sequence"]
            stop.load_position = n - entry["sequence"] + 1
            updated.append(stop)
        RouteStop.objects.bulk_update(updated, ["sequence", "load_position"])
        run.refresh_from_db()
        return Response(DeliveryRunSerializer(run).data)

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        run = self.get_object()
        if run.status not in {DeliveryRun.Status.DRAFT, DeliveryRun.Status.PLANNED}:
            return Response({"detail": f"Cannot lock a run in status {run.status}."}, status=400)

        from apps.manufacturing.services import generate_manufacturing_list

        run.status = DeliveryRun.Status.LOCKED
        run.locked_at = timezone.now()
        run.save(update_fields=["status", "locked_at"])
        generate_manufacturing_list(run)
        return Response(DeliveryRunSerializer(run).data)

    @action(detail=True, methods=["get"], url_path="export/csv")
    def export_csv(self, request, pk=None):
        return export_run_csv(self.get_object())

    @action(detail=True, methods=["get"], url_path="export/pdf")
    def export_pdf(self, request, pk=None):
        return export_run_pdf(self.get_object())

    @action(detail=False, methods=["get"])
    def suggestions(self, request):
        suggestions = suggest_delivery_runs()
        serializer = RegionSuggestionSerializer(
            [s.__dict__ for s in suggestions], many=True
        )
        return Response(serializer.data)


class DriverRunsTodayView(APIView):
    permission_classes = [IsDriver]

    def get(self, request):
        runs = DeliveryRun.objects.filter(
            driver=request.user,
            status__in=[DeliveryRun.Status.PLANNED, DeliveryRun.Status.LOCKED, DeliveryRun.Status.IN_PROGRESS],
        ).select_related("van").prefetch_related("stops__order")
        return Response(DeliveryRunSerializer(runs, many=True).data)


class DriverStopUpdateView(APIView):
    permission_classes = [IsDriver]

    def patch(self, request, run_id, stop_id):
        stop = RouteStop.objects.filter(
            pk=stop_id, delivery_run_id=run_id, delivery_run__driver=request.user
        ).first()
        if not stop:
            return Response({"detail": "Not found."}, status=404)
        serializer = RouteStopSerializer(stop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if serializer.validated_data.get("status") == RouteStop.Status.DELIVERED:
            stop.delivered_at = timezone.now()
            stop.save(update_fields=["delivered_at"])
        return Response(RouteStopSerializer(stop).data)


class DeliverySettingsView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response(DeliverySettingsSerializer(DeliverySettings.load()).data)

    def patch(self, request):
        settings_obj = DeliverySettings.load()
        serializer = DeliverySettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
