from django.urls import path
from . import views

urlpatterns = [
    path('logs/', views.AuditLogListView.as_view(), name='audit-log-list'),
    path('logs/<int:pk>/', views.AuditLogDetailView.as_view(), name='audit-log-detail'),
    path('anomalies/', views.AnomalyReportView.as_view(), name='anomaly-report'),
    path('export/', views.AuditLogExportView.as_view(), name='audit-log-export'),
]
