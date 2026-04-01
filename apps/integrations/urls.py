from django.urls import path
from . import views

urlpatterns = [
    path('api-keys/', views.APIKeyListView.as_view(), name='api-key-list'),
    path('api-keys/<int:pk>/', views.APIKeyDetailView.as_view(), name='api-key-detail'),
    path('api-keys/<int:pk>/rotate/', views.APIKeyRotateView.as_view(), name='api-key-rotate'),
    path('webhooks/', views.WebhookListView.as_view(), name='webhook-list'),
    path('webhooks/<int:pk>/', views.WebhookDetailView.as_view(), name='webhook-detail'),
    path('webhooks/<int:pk>/deliveries/', views.WebhookDeliveryListView.as_view(), name='webhook-deliveries'),
    path('webhooks/<int:pk>/test/', views.WebhookTestView.as_view(), name='webhook-test'),
]
