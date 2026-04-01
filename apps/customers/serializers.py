from rest_framework import serializers

from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for customer data."""

    class Meta:
        model = Customer
        fields = [
            'customer_id', 'full_name', 'phone', 'email', 'address',
            'birthday', 'loyalty_points', 'total_spent', 'registered_at',
        ]
        read_only_fields = ['customer_id', 'loyalty_points', 'total_spent', 'registered_at']

    def validate_phone(self, value):
        if not value:
            return value
        instance = self.instance
        qs = Customer.objects.filter(phone=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A customer with this phone number already exists.')
        return value

    def validate(self, attrs):
        if not attrs.get('phone') and not attrs.get('email'):
            raise serializers.ValidationError(
                'At least one contact method (phone or email) is required.'
            )
        return attrs


class CustomerUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating customer details."""

    class Meta:
        model = Customer
        fields = ['full_name', 'phone', 'email', 'address', 'birthday']

    def validate_phone(self, value):
        if not value:
            return value
        instance = self.instance
        qs = Customer.objects.filter(phone=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A customer with this phone number already exists.')
        return value


class CustomerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer lists."""

    class Meta:
        model = Customer
        fields = [
            'customer_id', 'full_name', 'phone', 'email',
            'loyalty_points', 'total_spent', 'registered_at',
        ]
