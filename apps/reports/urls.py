from django.urls import path

from .views import (
    CashierPerformanceView,
    CategoryRevenueReportView,
    CustomerReportView,
    DailySalesReportView,
    InventoryReportView,
    MonthlySalesReportView,
    PaymentMethodReportView,
    ProductPerformanceView,
    ReportExportView,
    WeeklySalesReportView,
)

urlpatterns = [
    path('daily/', DailySalesReportView.as_view(), name='report-daily'),
    path('weekly/', WeeklySalesReportView.as_view(), name='report-weekly'),
    path('monthly/', MonthlySalesReportView.as_view(), name='report-monthly'),
    path('products/', ProductPerformanceView.as_view(), name='report-products'),
    path('inventory/', InventoryReportView.as_view(), name='report-inventory'),
    path('cashiers/', CashierPerformanceView.as_view(), name='report-cashiers'),
    path('payment-methods/', PaymentMethodReportView.as_view(), name='report-payment-methods'),
    path('category-revenue/', CategoryRevenueReportView.as_view(), name='report-category-revenue'),
    path('customers/', CustomerReportView.as_view(), name='report-customers'),
    path('export/', ReportExportView.as_view(), name='report-export'),
]
