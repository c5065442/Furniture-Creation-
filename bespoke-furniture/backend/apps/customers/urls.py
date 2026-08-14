from rest_framework.routers import DefaultRouter

from .views import CustomerViewSet, DeliveryAddressViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("delivery-addresses", DeliveryAddressViewSet, basename="deliveryaddress")

urlpatterns = router.urls
