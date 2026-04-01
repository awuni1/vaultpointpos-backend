from django.db import models


class NotificationLog(models.Model):
    TYPE_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('daily_summary', 'Daily Summary'),
        ('loyalty_sms', 'Loyalty SMS'),
        ('receipt_email', 'Receipt Email'),
        ('receipt_sms', 'Receipt SMS'),
        ('shift_alert', 'Shift Alert'),
        ('lockout_alert', 'Lockout Alert'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    recipient = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.notification_type} → {self.recipient} [{self.status}]'


class NotificationSettings(models.Model):
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField()
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'notification_settings'
        verbose_name_plural = 'Notification Settings'

    def __str__(self):
        return self.setting_key
