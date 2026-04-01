from django.contrib import admin

from .models import Sale, SaleItem, TransactionLog


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['sale_item_id', 'line_total']
    fields = ['product', 'quantity', 'unit_price', 'discount_pct', 'line_total']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'sale_id', 'sale_date', 'user', 'customer', 'total_amount',
        'payment_method', 'status',
    ]
    list_filter = ['status', 'payment_method', 'sale_date']
    search_fields = ['sale_id', 'user__username', 'customer__full_name']
    readonly_fields = ['sale_id', 'sale_date', 'subtotal', 'tax_amount', 'total_amount']
    ordering = ['-sale_date']
    inlines = [SaleItemInline]

    fieldsets = (
        ('Sale Info', {'fields': ('sale_id', 'sale_date', 'user', 'customer', 'status', 'notes')}),
        ('Financials', {'fields': ('subtotal', 'discount_amount', 'tax_rate', 'tax_amount', 'total_amount')}),
        ('Payment', {'fields': ('payment_method',)}),
    )


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale_item_id', 'sale', 'product', 'quantity', 'unit_price', 'discount_pct', 'line_total']
    list_filter = ['sale__status']
    search_fields = ['product__product_name', 'sale__sale_id']
    readonly_fields = ['sale_item_id', 'line_total']


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = ['log_id', 'user', 'action', 'entity_type', 'entity_id', 'ip_address', 'created_at']
    list_filter = ['action', 'entity_type', 'created_at']
    search_fields = ['user__username', 'action', 'entity_id']
    readonly_fields = ['log_id', 'created_at']
    ordering = ['-created_at']
