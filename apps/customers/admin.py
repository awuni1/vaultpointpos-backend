from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'customer_id', 'full_name', 'phone', 'email',
        'loyalty_points', 'total_spent', 'registered_at',
    ]
    search_fields = ['full_name', 'phone', 'email']
    list_filter = ['registered_at']
    readonly_fields = ['customer_id', 'loyalty_points', 'total_spent', 'registered_at']
    ordering = ['-total_spent']
