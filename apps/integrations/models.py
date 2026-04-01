import secrets

from django.conf import settings
from django.db import models


def generate_api_key():
    return secrets.token_urlsafe(40)


def generate_webhook_secret():
    return secrets.token_hex(32)


class APIKey(models.Model):
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=60, unique=True, default=generate_api_key)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='api_keys')
    is_active = models.BooleanField(default=True)
    permissions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'api_keys'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.owner.username})'


class Webhook(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    events = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    secret = models.CharField(max_length=64, default=generate_webhook_secret)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webhooks'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} → {self.url}'


class WebhookDelivery(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    response_code = models.IntegerField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webhook_deliveries'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type} → {self.webhook.url} [{self.status}]'
