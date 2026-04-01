from django.urls import path

from .views import (
    CustomerDetailView,
    CustomerExportView,
    CustomerListView,
    CustomerPurchaseHistoryView,
    TopCustomersView,
)

urlpatterns = [
    path('', CustomerListView.as_view(), name='customer-list'),
    path('export/', CustomerExportView.as_view(), name='customer-export'),
    path('top/', TopCustomersView.as_view(), name='top-customers'),
    path('<int:customer_id>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('<int:customer_id>/history/', CustomerPurchaseHistoryView.as_view(), name='customer-history'),
]
