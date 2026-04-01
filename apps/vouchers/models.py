import secrets
import string

from django.conf import settings
from django.db import models


def generate_code(length=12):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class GiftCard(models.Model):
    code = models.CharField(max_length=20, unique=True, default=generate_code)
    initial_value = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='gift_cards_issued')
    customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='gift_cards')
    expires_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gift_cards'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.pk:
            self.remaining_balance = self.initial_value
        super().save(*args, **kwargs)

    def __str__(self):
        return f'GiftCard {self.code} (Balance: {self.remaining_balance})'


class Voucher(models.Model):
    TYPE_CHOICES = [
        ('percentage', 'Percentage Discount'),
        ('flat_amount', 'Flat Amount Off'),
        ('free_item', 'Free Item'),
    ]

    code = models.CharField(max_length=50, unique=True)
    voucher_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_uses = models.IntegerField(default=1)
    times_used = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateField(null=True, blank=True)
    minimum_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vouchers'
        ordering = ['-created_at']

    def is_valid(self):
        from django.utils import timezone
        if not self.is_active:
            return False, 'Voucher is inactive.'
        if self.times_used >= self.max_uses:
            return False, 'Voucher has been fully redeemed.'
        if self.expires_at and self.expires_at < timezone.now().date():
            return False, 'Voucher has expired.'
        return True, 'Valid'

    def __str__(self):
        return f'{self.code} ({self.voucher_type}: {self.discount_value})'


class VoucherRedemption(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='redemptions')
    sale = models.ForeignKey('sales.Sale', on_delete=models.CASCADE, related_name='voucher_redemptions')
    amount_discounted = models.DecimalField(max_digits=10, decimal_places=2)
    redeemed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'voucher_redemptions'

    def __str__(self):
        return f'{self.voucher.code} redeemed on sale #{self.sale_id}'
