import uuid
from django.db import models


class Payment(models.Model):
    """Records payment information for a sale."""

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Card'),
    ]

    payment_id = models.AutoField(primary_key=True)
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.CASCADE,
        related_name='payments',
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference_number = models.CharField(max_length=100, null=True, blank=True)  # MoMo/card ref
    card_last_four = models.CharField(max_length=4, null=True, blank=True)
    amount_tendered = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    change_due = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f'Payment #{self.payment_id} - {self.payment_method} {self.amount}'


class MobileMoneyQR(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]

    sale = models.OneToOneField('sales.Sale', on_delete=models.CASCADE, related_name='momo_qr')
    qr_code_data = models.TextField()
    qr_code_image_b64 = models.TextField(blank=True, default='')
    merchant_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    transaction_ref = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'momo_qr_codes'

    def __str__(self):
        return f'MoMo QR for Sale #{self.sale_id} [{self.status}]'


class PaystackTransaction(models.Model):
    """Tracks a Paystack Mobile Money charge from initiation to completion."""

    PROVIDER_CHOICES = [
        ('mtn', 'MTN MoMo'),
        ('vodafone', 'Vodafone Cash'),
        ('airteltigo', 'AirtelTigo Money'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('pay_offline', 'Awaiting Customer Approval'),
        ('send_otp', 'Awaiting OTP'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    sale = models.OneToOneField(
        'sales.Sale', on_delete=models.CASCADE, related_name='paystack_transaction'
    )
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone = models.CharField(max_length=20)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    customer_email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paystack_status = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'paystack_transactions'

    def __str__(self):
        return f'Paystack {self.reference} [{self.status}]'

    @staticmethod
    def generate_reference(sale_id):
        return f'SWFTPS-{sale_id}-{uuid.uuid4().hex[:8]}'
