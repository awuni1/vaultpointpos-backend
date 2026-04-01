from rest_framework import serializers
from .models import APIKey, Webhook, WebhookDelivery


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ('id', 'name', 'key', 'owner', 'is_active', 'permissions', 'created_at', 'last_used_at')
        read_only_fields = ('key', 'owner', 'created_at', 'last_used_at')


class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = ('id', 'name', 'url', 'events', 'is_active', 'created_by', 'created_at')
        read_only_fields = ('secret', 'created_by', 'created_at')


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = '__all__'
