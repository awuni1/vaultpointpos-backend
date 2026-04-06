from django.urls import path

from .views import (
    DailyCashReconciliationView,
    PaymentListView,
    GenerateMoMoQRView,
    MoMoStatusView,
    MoMoConfirmView,
    InitiateMoMoPaymentView,
    SubmitMoMoOTPView,
    VerifyPaystackPaymentView,
    PaystackWebhookView,
)

urlpatterns = [
    path('', PaymentListView.as_view(), name='payment-list'),
    path('reconciliation/', DailyCashReconciliationView.as_view(), name='cash-reconciliation'),

    # Legacy QR-based MoMo (kept for backwards compatibility)
    path('momo/generate/', GenerateMoMoQRView.as_view(), name='momo-generate'),
    path('momo/<int:sale_id>/status/', MoMoStatusView.as_view(), name='momo-status'),
    path('momo/<int:sale_id>/confirm/', MoMoConfirmView.as_view(), name='momo-confirm'),

    # Paystack MoMo (real integration)
    path('momo/initiate/', InitiateMoMoPaymentView.as_view(), name='momo-initiate'),
    path('momo/submit-otp/', SubmitMoMoOTPView.as_view(), name='momo-submit-otp'),
    path('paystack/verify/', VerifyPaystackPaymentView.as_view(), name='paystack-verify'),
    path('paystack/webhook/', PaystackWebhookView.as_view(), name='paystack-webhook'),
]
