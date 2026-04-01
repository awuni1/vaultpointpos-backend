from django.conf import settings
from django.db import models


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    payment_terms = models.CharField(max_length=100, blank=True, default='')
    lead_time_days = models.IntegerField(default=7)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'suppliers'
        ordering = ['name']

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]

    po_number = models.CharField(max_length=30, unique=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    branch = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='purchase_orders_created')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders_approved')
    expected_delivery = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'purchase_orders'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.po_number:
            last = PurchaseOrder.objects.order_by('-id').first()
            next_id = (last.id + 1) if last else 1
            from django.utils import timezone
            self.po_number = f'PO-{timezone.now().year}-{next_id:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.po_number


class PurchaseOrderItem(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity_ordered = models.IntegerField()
    quantity_received = models.IntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'purchase_order_items'

    def save(self, *args, **kwargs):
        self.line_total = self.unit_cost * self.quantity_ordered
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.po.po_number} - {self.product.product_name}'


class SupplierPerformance(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='performance_records')
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    ordered_qty = models.IntegerField()
    received_qty = models.IntegerField()
    on_time = models.BooleanField(default=True)
    delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'supplier_performance'

    def __str__(self):
        return f'{self.supplier.name} - {self.po.po_number}'
