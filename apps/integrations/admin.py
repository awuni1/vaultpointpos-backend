from django.contrib import admin
from .models import APIKey, Webhook, WebhookDelivery

admin.site.register(APIKey)
admin.site.register(Webhook)
admin.site.register(WebhookDelivery)
