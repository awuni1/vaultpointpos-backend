from django.conf import settings
from django.db import models


class Branch(models.Model):
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'branches'
        ordering = ['name']
        verbose_name_plural = 'Branches'

    def __str__(self):
        return self.name


class BranchInventory(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='inventory')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='branch_inventory')
    quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=5)

    class Meta:
        db_table = 'branch_inventory'
        unique_together = ('branch', 'product')

    def __str__(self):
        return f'{self.branch.name} - {self.product.product_name}: {self.quantity}'


class StockTransfer(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    from_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='transfers_out')
    to_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='transfers_in')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='transfers_requested')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers_approved')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stock_transfers'
        ordering = ['-created_at']

    def __str__(self):
        return f'Transfer {self.product.product_name} x{self.quantity}: {self.from_branch} → {self.to_branch}'
