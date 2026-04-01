from django.urls import path
from . import views

urlpatterns = [
    path('', views.SupplierListView.as_view(), name='supplier-list'),
    path('<int:pk>/', views.SupplierDetailView.as_view(), name='supplier-detail'),
    path('<int:pk>/performance/', views.SupplierPerformanceView.as_view(), name='supplier-performance'),
    path('orders/', views.PurchaseOrderListView.as_view(), name='po-list'),
    path('orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='po-detail'),
    path('orders/<int:pk>/approve/', views.PurchaseOrderApproveView.as_view(), name='po-approve'),
    path('orders/<int:pk>/receive/', views.PurchaseOrderReceiveView.as_view(), name='po-receive'),
]
