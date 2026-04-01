"""
SwiftPOS URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # API routes — core
    path('api/auth/', include('apps.authentication.urls')),
    path('api/products/', include('apps.products.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/sales/', include('apps.sales.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/customers/', include('apps.customers.urls')),
    path('api/receipts/', include('apps.receipts.urls')),
    path('api/reports/', include('apps.reports.urls')),

    # API routes — enhancements
    path('api/branches/', include('apps.branches.urls')),
    path('api/shifts/', include('apps.shifts.urls')),
    path('api/expenses/', include('apps.expenses.urls')),
    path('api/suppliers/', include('apps.suppliers.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/vouchers/', include('apps.vouchers.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/tables/', include('apps.tables.urls')),
    path('api/targets/', include('apps.targets.urls')),
    path('api/forecasting/', include('apps.forecasting.urls')),
    path('api/integrations/', include('apps.integrations.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
