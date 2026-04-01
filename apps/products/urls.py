from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ProductViewSet, BarcodeGenerateView, QRCodeGenerateView, BulkBarcodePDFView, ProductBulkImportView, BarcodeLookupView

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'', ProductViewSet, basename='product')

urlpatterns = [
    path('import/', ProductBulkImportView.as_view(), name='product-bulk-import'),
    path('', include(router.urls)),
    path('barcode/lookup/<str:barcode>/', BarcodeLookupView.as_view(), name='product-barcode-lookup'),
    path('<int:pk>/barcode/', BarcodeGenerateView.as_view(), name='product-barcode'),
    path('<int:pk>/qrcode/', QRCodeGenerateView.as_view(), name='product-qrcode'),
    path('barcodes/bulk/', BulkBarcodePDFView.as_view(), name='product-bulk-barcodes'),
]
