from django.contrib import admin

from .models import StockMovement, SupplierDelivery


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'movement_id', 'product', 'movement_type', 'quantity_change',
        'quantity_before', 'quantity_after', 'user', 'created_at',
    ]
    list_filter = ['movement_type', 'created_at']
    search_fields = ['product__product_name', 'reason', 'reference_id']
    readonly_fields = ['movement_id', 'created_at']
    ordering = ['-created_at']


@admin.register(SupplierDelivery)
class SupplierDeliveryAdmin(admin.ModelAdmin):
    list_display = [
        'delivery_id', 'product', 'supplier_name', 'quantity_received',
        'unit_cost', 'delivery_date', 'user', 'created_at',
    ]
    list_filter = ['supplier_name', 'delivery_date']
    search_fields = ['product__product_name', 'supplier_name']
    readonly_fields = ['delivery_id', 'created_at']
    ordering = ['-delivery_date']
