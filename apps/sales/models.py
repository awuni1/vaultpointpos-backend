from django.db import models
from django.conf import settings


class Sale(models.Model):
    """Represents a completed sale transaction."""

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Card'),
        ('split', 'Split Payment'),
    ]

    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
        ('voided', 'Voided'),
        ('held', 'Held'),
    ]

    sale_id = models.AutoField(primary_key=True)
    sale_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales',
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'sales'
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        ordering = ['-sale_date']

    def __str__(self):
        return f'Sale #{self.sale_id} - {self.total_amount} ({self.status})'


class SaleItem(models.Model):
    """Individual line item within a sale."""

    sale_item_id = models.AutoField(primary_key=True)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        related_name='sale_items',
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Snapshot at time of sale
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'sale_items'
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'

    def __str__(self):
        return f'Sale #{self.sale_id} - {self.product.product_name if self.product else "Unknown"} x{self.quantity}'

    def calculate_line_total(self):
        """Calculate line total applying discount."""
        discount_multiplier = 1 - (self.discount_pct / 100)
        return self.unit_price * self.quantity * discount_multiplier


class TransactionLog(models.Model):
    """Audit log for all system actions."""

    log_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transaction_logs',
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50, null=True, blank=True)
    entity_id = models.CharField(max_length=50, null=True, blank=True)
    details = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transaction_logs'
        verbose_name = 'Transaction Log'
        verbose_name_plural = 'Transaction Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} by {self.user} at {self.created_at}'
