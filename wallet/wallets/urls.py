from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny

from wallets.views import (
    CreateDepositView,
    CreateWalletView,
    RetrieveWalletView,
    ScheduleWithdrawView,
    WithdrawalCancellationView,
)

schema_view = get_schema_view(
    openapi.Info(
        title="Wallet API",
        default_version="v1",
        description="API documentation",
    ),
    public=True,
    permission_classes=(AllowAny,),
)

api_urlpatterns = [
    path("create/", CreateWalletView.as_view(), name="create-wallet"),
    path("<uuid:uuid>/", RetrieveWalletView.as_view(), name="retrieve-wallet"),
    path(
        "<uuid:wallet_uuid>/deposit",
        CreateDepositView.as_view(),
        name="deposit",
    ),
    path(
        "<uuid:wallet_uuid>/withdrawl",
        ScheduleWithdrawView.as_view(),
        name="withdraw",
    ),
    path(
        "withdrawl/cancel",
        WithdrawalCancellationView.as_view(),
        name="cancel-withdrawal",
    ),
]

swagger_urlpatterns = [
    path(
        "",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        ".<format>",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json-or-yaml",
    ),
]

urlpatterns = [
    path("swagger/", include(swagger_urlpatterns)),
    path("wallets/", include(api_urlpatterns)),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
