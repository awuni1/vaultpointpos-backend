from django.urls import path

from .views import ReceiptDetailView, ReceiptPDFView

urlpatterns = [
    path('<int:sale_id>/', ReceiptDetailView.as_view(), name='receipt-detail'),
    path('<int:sale_id>/pdf/', ReceiptPDFView.as_view(), name='receipt-pdf'),
]
