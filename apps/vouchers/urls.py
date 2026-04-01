from django.urls import path
from . import views

urlpatterns = [
    path('gift-cards/', views.GiftCardCreateView.as_view(), name='gift-card-list'),
    path('gift-cards/<str:code>/balance/', views.GiftCardBalanceView.as_view(), name='gift-card-balance'),
    path('gift-cards/<str:code>/redeem/', views.GiftCardRedeemView.as_view(), name='gift-card-redeem'),
    path('', views.VoucherViewSet.as_view(), name='voucher-list'),
    path('<int:pk>/', views.VoucherDetailView.as_view(), name='voucher-detail'),
    path('validate/', views.VoucherValidateView.as_view(), name='voucher-validate'),
    path('redeem/', views.VoucherRedeemView.as_view(), name='voucher-redeem'),
]
