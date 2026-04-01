from django.urls import path

from .views import (
    ActiveSaleDisplayView,
    CustomerDisplayView,
    SaleCreateView,
    SaleDetailView,
    SaleHoldView,
    SaleListView,
    SaleRefundView,
    SaleResumeView,
    SaleVoidView,
)

urlpatterns = [
    path('', SaleListView.as_view(), name='sale-list'),
    path('create/', SaleCreateView.as_view(), name='sale-create'),
    path('<int:sale_id>/', SaleDetailView.as_view(), name='sale-detail'),
    path('<int:sale_id>/void/', SaleVoidView.as_view(), name='sale-void'),
    path('<int:sale_id>/refund/', SaleRefundView.as_view(), name='sale-refund'),
    path('<int:sale_id>/hold/', SaleHoldView.as_view(), name='sale-hold'),
    path('<int:sale_id>/resume/', SaleResumeView.as_view(), name='sale-resume'),
    path('display/<int:sale_id>/', CustomerDisplayView.as_view(), name='customer-display'),
    path('display/active/<str:cashier_id>/', ActiveSaleDisplayView.as_view(), name='active-sale-display'),
]
