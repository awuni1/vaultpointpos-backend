from django.urls import path
from . import views

urlpatterns = [
    path('products/<int:pk>/', views.ProductForecastView.as_view(), name='product-forecast'),
    path('store/', views.StoreForecastView.as_view(), name='store-forecast'),
    path('stockout-risk/', views.LowStockForecastView.as_view(), name='stockout-risk'),
    path('run/', views.RunForecastView.as_view(), name='run-forecast'),
]
