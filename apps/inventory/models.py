from django.db import models
from django.conf import settings


class StockMovement(models.Model):
    """Records every change in stock levels for audit purposes."""

    MOVEMENT_TYPE_CHOICES = [
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('receive', 'Receive'),
        ('return', 'Return'),
    ]

    movement_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='stock_movements',
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    quantity_change = models.IntegerField()  # Positive = added, negative = removed
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    reason = models.TextField(null=True, blank=True)
    reference_id = models.CharField(max_length=100, null=True, blank=True)  # e.g. sale_id
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_movements',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_movements'
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        ordering = ['-created_at']

    def __str__(self):
        direction = '+' if self.quantity_change >= 0 else ''
        return (
            f'{self.product.product_name}: {direction}{self.quantity_change} '
            f'({self.movement_type}) on {self.created_at.date()}'
        )


class SupplierDelivery(models.Model):
    """Records stock received from suppliers."""

    delivery_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='supplier_deliveries',
    )
    supplier_name = models.CharField(max_length=255)
    quantity_received = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_date = models.DateField()
    notes = models.TextField(null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='supplier_deliveries',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'supplier_deliveries'
        verbose_name = 'Supplier Delivery'
        verbose_name_plural = 'Supplier Deliveries'
        ordering = ['-delivery_date']

    def __str__(self):
        return (
            f'{self.supplier_name} → {self.product.product_name}: '
            f'{self.quantity_received} units on {self.delivery_date}'
        )
