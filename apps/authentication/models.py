import uuid
from decimal import Decimal

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager for User model."""

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The username field is required.')
        extra_fields.setdefault('is_active', True)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model for SwiftPOS with role-based access control."""

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('cashier', 'Cashier'),
    ]

    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name']

    class Meta:
        db_table = 'auth_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.username} ({self.role})'

    def is_locked_out(self):
        """Check if the account is currently locked out."""
        if self.lockout_until and self.lockout_until > timezone.now():
            return True
        return False

    def increment_failed_attempts(self):
        """Increment failed login attempts and lock account if threshold reached."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.lockout_until = timezone.now() + timezone.timedelta(minutes=15)
        self.save(update_fields=['failed_login_attempts', 'lockout_until'])

    def reset_failed_attempts(self):
        """Reset failed login attempts after successful login."""
        self.failed_login_attempts = 0
        self.lockout_until = None
        self.last_login = timezone.now()
        self.save(update_fields=['failed_login_attempts', 'lockout_until', 'last_login'])


class PasswordResetOTP(models.Model):
    """Stores one-time passwords for user password reset requests."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_otps',
    )
    otp = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'password_reset_otps'
        verbose_name = 'Password Reset OTP'
        verbose_name_plural = 'Password Reset OTPs'
        ordering = ['-created_at']

    def is_valid(self):
        """Check if OTP is still valid (not used and not expired)."""
        return not self.used and self.expires_at > timezone.now()

    def __str__(self):
        return f'OTP for {self.user.username} (expires: {self.expires_at})'


class SystemSettings(models.Model):
    """Singleton model for global system/store configuration."""

    store_name = models.CharField(max_length=255, default='SwiftPOS Store')
    store_address = models.TextField(blank=True, default='')
    store_phone = models.CharField(max_length=30, blank=True, default='')
    store_email = models.EmailField(blank=True, default='')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    receipt_footer = models.TextField(blank=True, default='Thank you for your purchase!')
    currency_symbol = models.CharField(max_length=10, default='GHS')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_settings'
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'

    @classmethod
    def get_settings(cls):
        """Return the singleton settings instance, creating it if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'System Settings ({self.store_name})'
