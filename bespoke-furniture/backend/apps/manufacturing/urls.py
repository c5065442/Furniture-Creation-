from rest_framework.routers import DefaultRouter

from .views import ManufacturingListViewSet

router = DefaultRouter()
router.register("manufacturing-lists", ManufacturingListViewSet, basename="manufacturinglist")

urlpatterns = router.urls
