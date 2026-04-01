from django.conf import settings
from django.db import models


class SalesTarget(models.Model):
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='sales_targets')
    branch = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='targets_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_targets'
        ordering = ['-start_date']

    def __str__(self):
        user = self.cashier.username if self.cashier else 'Store'
        return f'{user} {self.period_type} target: {self.target_amount}'


class Achievement(models.Model):
    CONDITION_CHOICES = [
        ('sales_count', 'Sales Count'),
        ('revenue', 'Revenue'),
        ('no_voids', 'No Voids'),
        ('transactions_in_day', 'Transactions in a Day'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    badge_icon = models.CharField(max_length=100, default='🏆')
    condition_type = models.CharField(max_length=30, choices=CONDITION_CHOICES)
    condition_value = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'achievements'

    def __str__(self):
        return self.name


class CashierAchievement(models.Model):
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    sale = models.ForeignKey('sales.Sale', on_delete=models.SET_NULL, null=True, blank=True)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cashier_achievements'
        unique_together = ('cashier', 'achievement')

    def __str__(self):
        return f'{self.cashier.username} earned {self.achievement.name}'
