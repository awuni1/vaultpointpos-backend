from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'full_name', 'email', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['username', 'full_name', 'email']
    ordering = ['-created_at']
    readonly_fields = ['user_id', 'created_at', 'last_login']

    fieldsets = (
        (None, {'fields': ('user_id', 'username', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'email')}),
        ('Role & Status', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Login Info', {'fields': ('last_login', 'failed_login_attempts', 'lockout_until', 'created_at')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'full_name', 'email', 'role', 'password1', 'password2'),
        }),
    )
