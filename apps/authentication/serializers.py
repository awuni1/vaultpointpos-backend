from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User, SystemSettings


class UserSerializer(serializers.ModelSerializer):
    """Serializer for full user data."""

    class Meta:
        model = User
        fields = [
            'user_id', 'username', 'full_name', 'email', 'role',
            'is_active', 'created_at', 'last_login',
            'failed_login_attempts', 'lockout_until',
        ]
        read_only_fields = [
            'user_id', 'created_at', 'last_login',
            'failed_login_attempts', 'lockout_until',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }


class UserPublicSerializer(serializers.ModelSerializer):
    """Serializer for public/minimal user data (e.g., in tokens)."""

    class Meta:
        model = User
        fields = ['user_id', 'username', 'full_name', 'email', 'role', 'is_active']
        read_only_fields = ['user_id']


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if not username or not password:
            raise serializers.ValidationError('Both username and password are required.')

        return attrs


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for creating a new user (admin only)."""

    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'full_name', 'email', 'role',
            'password', 'confirm_password',
        ]

    def validate_role(self, value):
        valid_roles = ['admin', 'manager', 'cashier']
        if value not in valid_roles:
            raise serializers.ValidationError(
                f'Invalid role. Must be one of: {", ".join(valid_roles)}'
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password."""

    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    confirm_new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs.get('new_password') != attrs.get('confirm_new_password'):
            raise serializers.ValidationError(
                {'confirm_new_password': 'New passwords do not match.'}
            )
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user details."""

    class Meta:
        model = User
        fields = ['full_name', 'email', 'role', 'is_active']

    def validate_email(self, value):
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value


class SystemSettingsSerializer(serializers.ModelSerializer):
    """Serializer for system-wide settings."""

    class Meta:
        model = SystemSettings
        fields = [
            'store_name', 'store_address', 'store_phone', 'store_email',
            'tax_rate', 'receipt_footer', 'currency_symbol',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
