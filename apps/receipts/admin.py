from django.contrib import admin

from .models import Receipt


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_id', 'sale', 'generated_at', 'pdf_path']
    search_fields = ['sale__sale_id']
    readonly_fields = ['receipt_id', 'generated_at']
    ordering = ['-generated_at']
