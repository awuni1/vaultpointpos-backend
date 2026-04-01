from django.conf import settings
from django.db import models


class Shift(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
    ]

    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shifts')
    branch = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='shifts')
    opening_float = models.DecimalField(max_digits=10, decimal_places=2)
    closing_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expected_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    variance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'shifts'
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.cashier.username} shift started {self.started_at:%Y-%m-%d %H:%M}'

    def calculate_expected_cash(self):
        """Sum all cash sales during this shift plus opening float."""
        from apps.sales.models import Sale
        from django.db.models import Sum
        qs = Sale.objects.filter(
            user=self.cashier,
            status='completed',
            payment_method='cash',
            sale_date__gte=self.started_at,
        )
        if self.ended_at:
            qs = qs.filter(sale_date__lte=self.ended_at)
        cash_sales = qs.aggregate(total=Sum('total_amount'))['total'] or 0
        return self.opening_float + cash_sales
