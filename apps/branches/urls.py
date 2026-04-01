from django.urls import path
from . import views

urlpatterns = [
    path('', views.BranchListView.as_view(), name='branch-list'),
    path('<int:pk>/', views.BranchDetailView.as_view(), name='branch-detail'),
    path('<int:pk>/inventory/', views.BranchInventoryView.as_view(), name='branch-inventory'),
    path('transfers/', views.StockTransferView.as_view(), name='stock-transfer-list'),
    path('transfers/<int:pk>/approve/', views.StockTransferApproveView.as_view(), name='stock-transfer-approve'),
    path('reports/consolidated/', views.ConsolidatedReportView.as_view(), name='consolidated-report'),
]
