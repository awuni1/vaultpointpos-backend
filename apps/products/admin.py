from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_id', 'name', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'product_id', 'product_name', 'category', 'price',
        'cost_price', 'quantity', 'barcode', 'reorder_level',
        'is_active', 'created_at',
    ]
    list_filter = ['is_active', 'category', 'created_at']
    search_fields = ['product_name', 'barcode']
    list_editable = ['price', 'quantity', 'is_active']
    ordering = ['product_name']
    readonly_fields = ['product_id', 'created_at', 'updated_at']

    fieldsets = (
        ('Product Info', {'fields': ('product_id', 'product_name', 'category', 'barcode', 'image_url')}),
        ('Pricing', {'fields': ('price', 'cost_price')}),
        ('Inventory', {'fields': ('quantity', 'reorder_level', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
