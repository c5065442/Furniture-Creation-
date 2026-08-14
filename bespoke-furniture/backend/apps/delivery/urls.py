from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DeliveryRunViewSet,
    DeliverySettingsView,
    DriverRunsTodayView,
    DriverStopUpdateView,
    VanViewSet,
)

router = DefaultRouter()
router.register("vans", VanViewSet, basename="van")
router.register("delivery-runs", DeliveryRunViewSet, basename="deliveryrun")

urlpatterns = router.urls + [
    path("delivery-settings/", DeliverySettingsView.as_view(), name="delivery-settings"),
    path("driver/runs/today/", DriverRunsTodayView.as_view(), name="driver-runs-today"),
    path(
        "delivery-runs/<int:run_id>/stops/<int:stop_id>/",
        DriverStopUpdateView.as_view(),
        name="driver-stop-update",
    ),
]
