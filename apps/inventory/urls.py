from django.urls import path

from .views import (
    DeadStockView,
    InventoryExportView,
    InventoryListView,
    LowStockView,
    ReceiveStockView,
    ReorderSuggestionsView,
    StockAdjustmentView,
    StockMovementListView,
)

urlpatterns = [
    path('', InventoryListView.as_view(), name='inventory-list'),
    path('adjust/', StockAdjustmentView.as_view(), name='stock-adjustment'),
    path('receive/', ReceiveStockView.as_view(), name='receive-stock'),
    path('movements/', StockMovementListView.as_view(), name='stock-movements'),
    path('low-stock/', LowStockView.as_view(), name='low-stock'),
    path('dead-stock/', DeadStockView.as_view(), name='dead-stock'),
    path('export/', InventoryExportView.as_view(), name='inventory-export'),
    path('reorder-suggestions/', ReorderSuggestionsView.as_view(), name='reorder-suggestions'),
]
