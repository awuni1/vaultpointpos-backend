from django.urls import path
from . import views

urlpatterns = [
    path('receipt-email/', views.SendReceiptEmailView.as_view(), name='receipt-email'),
    path('receipt-sms/', views.SendReceiptSMSView.as_view(), name='receipt-sms'),
    path('low-stock-alert/', views.LowStockAlertView.as_view(), name='low-stock-alert'),
    path('daily-summary/', views.DailySummaryEmailView.as_view(), name='daily-summary'),
    path('logs/', views.NotificationLogListView.as_view(), name='notification-logs'),
]
