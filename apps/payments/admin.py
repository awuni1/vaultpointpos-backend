from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 'sale', 'payment_method', 'amount',
        'reference_number', 'card_last_four', 'created_at',
    ]
    list_filter = ['payment_method', 'created_at']
    search_fields = ['sale__sale_id', 'reference_number', 'card_last_four']
    readonly_fields = ['payment_id', 'created_at']
    ordering = ['-created_at']
