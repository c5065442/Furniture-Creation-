from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET


@csrf_exempt
@require_GET
def api_root(request):
    return JsonResponse(
        {
            "service": "Bespoke Furniture Creations API",
            "status": "ok",
            "admin": request.build_absolute_uri("/admin/"),
            "api_v1": request.build_absolute_uri("/api/v1/"),
        }
    )


@csrf_exempt
@require_GET
def api_index(request):
    return JsonResponse(
        {
            "service": "Bespoke Furniture Creations API",
            "available_versions": ["v1"],
            "v1": request.build_absolute_uri("/api/v1/"),
        }
    )


urlpatterns = [
    path("", api_root),
    path("api/", api_index),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.products.urls")),
    path("api/v1/", include("apps.customers.urls")),
    path("api/v1/", include("apps.orders.urls")),
    path("api/v1/", include("apps.delivery.urls")),
    path("api/v1/", include("apps.manufacturing.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
