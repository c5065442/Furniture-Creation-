from rest_framework.routers import DefaultRouter

from .views import FinishOptionViewSet, ProductCategoryViewSet, ProductVariantViewSet, ProductViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("product-variants", ProductVariantViewSet, basename="productvariant")
router.register("categories", ProductCategoryViewSet, basename="productcategory")
router.register("finish-options", FinishOptionViewSet, basename="finishoption")

urlpatterns = router.urls
