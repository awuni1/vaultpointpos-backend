from django.db import models


class Customer(models.Model):
    """Customer model for loyalty tracking and purchase history."""

    customer_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    loyalty_points = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-registered_at']

    def __str__(self):
        return f'{self.full_name} ({self.phone or self.email or "No contact"})'

    def add_loyalty_points(self, amount):
        """Add loyalty points based on purchase amount (1 point per unit spent)."""
        points_earned = int(amount)
        self.loyalty_points += points_earned
        return points_earned

    def update_spending(self, amount):
        """Update total spending and loyalty points after a purchase."""
        self.total_spent += amount
        points_earned = self.add_loyalty_points(amount)
        self.save(update_fields=['loyalty_points', 'total_spent'])
        return points_earned
