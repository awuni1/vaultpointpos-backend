from rest_framework import serializers
from .models import NotificationLog, NotificationSettings


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = '__all__'


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        fields = '__all__'


class SendReceiptEmailSerializer(serializers.Serializer):
    sale_id = serializers.IntegerField()
    email = serializers.EmailField()


class SendReceiptSMSSerializer(serializers.Serializer):
    sale_id = serializers.IntegerField()
    phone = serializers.CharField(max_length=20)
