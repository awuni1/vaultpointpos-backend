from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminPasswordResetView,
    ChangePasswordView,
    ConfirmPasswordResetView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    RequestPasswordResetView,
    SystemSettingsView,
    UserDetailView,
    UserListView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<uuid:user_id>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<uuid:user_id>/reset-password/', AdminPasswordResetView.as_view(), name='admin-password-reset'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('password-reset/request/', RequestPasswordResetView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', ConfirmPasswordResetView.as_view(), name='password-reset-confirm'),
    path('settings/', SystemSettingsView.as_view(), name='system-settings'),
]
