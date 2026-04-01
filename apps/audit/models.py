from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('void', 'Void'),
        ('refund', 'Refund'),
        ('price_change', 'Price Change'),
        ('stock_adjust', 'Stock Adjustment'),
        ('role_change', 'Role Change'),
        ('login_failed', 'Login Failed'),
        ('account_locked', 'Account Locked'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=50, blank=True, default='')
    entity_id = models.CharField(max_length=50, blank=True, default='')
    before_value = models.JSONField(null=True, blank=True)
    after_value = models.JSONField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, blank=True, default='')
    user_agent = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f'{self.action} on {self.entity_type}/{self.entity_id} by {self.user}'
