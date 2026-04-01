from django.urls import path

from .views import DailyCashReconciliationView, PaymentListView, GenerateMoMoQRView, MoMoStatusView, MoMoConfirmView

urlpatterns = [
    path('', PaymentListView.as_view(), name='payment-list'),
    path('reconciliation/', DailyCashReconciliationView.as_view(), name='cash-reconciliation'),
    path('momo/generate/', GenerateMoMoQRView.as_view(), name='momo-generate'),
    path('momo/<int:sale_id>/status/', MoMoStatusView.as_view(), name='momo-status'),
    path('momo/<int:sale_id>/confirm/', MoMoConfirmView.as_view(), name='momo-confirm'),
]
