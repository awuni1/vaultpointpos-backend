from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User, PasswordResetOTP, SystemSettings
from .permissions import IsAdmin
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    SystemSettingsSerializer,
    UserPublicSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


def log_transaction(user, action, entity_type=None, entity_id=None, details=None, ip_address=None):
    """Helper to log actions to TransactionLog without circular imports."""
    try:
        from apps.sales.models import TransactionLog
        TransactionLog.objects.create(
            user=user,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details or {},
            ip_address=ip_address,
        )
    except Exception:
        pass


def get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class LoginView(APIView):
    """Handle user login and return JWT tokens."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        ip_address = get_client_ip(request)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check account lockout
        if user.is_locked_out():
            remaining = (user.lockout_until - timezone.now()).seconds // 60
            return Response(
                {
                    'error': 'Account is temporarily locked due to too many failed attempts.',
                    'lockout_until': user.lockout_until,
                    'retry_after_minutes': remaining,
                },
                status=status.HTTP_423_LOCKED
            )

        # Validate password
        if not user.check_password(password):
            user.increment_failed_attempts()
            attempts_left = max(0, 5 - user.failed_login_attempts)
            log_transaction(
                user=None,
                action='login_failed',
                entity_type='user',
                entity_id=user.user_id,
                details={'username': username, 'reason': 'invalid_password'},
                ip_address=ip_address,
            )
            return Response(
                {
                    'error': 'Invalid credentials.',
                    'attempts_remaining': attempts_left,
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check if user is active
        if not user.is_active:
            return Response(
                {'error': 'This account has been deactivated.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Successful login
        user.reset_failed_attempts()

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        log_transaction(
            user=user,
            action='login',
            entity_type='user',
            entity_id=user.user_id,
            details={'username': username},
            ip_address=ip_address,
        )

        return Response(
            {
                'access': str(access_token),
                'refresh': str(refresh),
                'user': UserPublicSerializer(user).data,
            },
            status=status.HTTP_200_OK
        )


class LogoutView(APIView):
    """Handle user logout by blacklisting the refresh token."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        log_transaction(
            user=request.user,
            action='logout',
            entity_type='user',
            entity_id=request.user.user_id,
            details={'username': request.user.username},
            ip_address=get_client_ip(request),
        )

        return Response(
            {'message': 'Successfully logged out.'},
            status=status.HTTP_200_OK
        )


class RegisterView(APIView):
    """Register a new user. Public endpoint."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        # Only log audit trail if the request comes from an authenticated user
        if request.user and request.user.is_authenticated:
            log_transaction(
                user=request.user,
                action='user_created',
                entity_type='user',
                entity_id=user.user_id,
                details={'username': user.username, 'role': user.role},
                ip_address=get_client_ip(request),
            )

        return Response(
            {
                'message': 'User created successfully.',
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED
        )


class UserListView(APIView):
    """List all users. Admin only."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        users = User.objects.all().order_by('-created_at')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserDetailView(APIView):
    """Get or update a specific user."""

    permission_classes = [IsAuthenticated]

    def get_object(self, user_id):
        try:
            return User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return None

    def get(self, request, user_id):
        # Users can view their own profile; admins can view anyone
        if str(request.user.user_id) != str(user_id) and request.user.role != 'admin':
            return Response(
                {'error': 'You do not have permission to view this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        user = self.get_object(user_id)
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    def put(self, request, user_id):
        if str(request.user.user_id) != str(user_id) and request.user.role != 'admin':
            return Response(
                {'error': 'You do not have permission to update this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        user = self.get_object(user_id)
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Only admins can change roles
        if 'role' in request.data and request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can change user roles.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UserUpdateSerializer(user, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    def patch(self, request, user_id):
        if str(request.user.user_id) != str(user_id) and request.user.role != 'admin':
            return Response(
                {'error': 'You do not have permission to update this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        user = self.get_object(user_id)
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if 'role' in request.data and request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can change user roles.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """Change the current user's password."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        log_transaction(
            user=request.user,
            action='password_changed',
            entity_type='user',
            entity_id=request.user.user_id,
            details={'username': request.user.username},
            ip_address=get_client_ip(request),
        )

        return Response(
            {'message': 'Password changed successfully.'},
            status=status.HTTP_200_OK
        )


class MeView(APIView):
    """Return the currently authenticated user's info."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserPublicSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminPasswordResetView(APIView):
    """Admin sets a new password for any user."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, user_id):
        try:
            target_user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_password = request.data.get('new_password')
        if not new_password or len(new_password) < 8:
            return Response(
                {'error': 'new_password must be at least 8 characters.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        target_user.set_password(new_password)
        target_user.save()

        log_transaction(
            user=request.user,
            action='password_changed',
            entity_type='user',
            entity_id=target_user.user_id,
            details={'admin_reset': True, 'target_username': target_user.username},
            ip_address=get_client_ip(request),
        )

        return Response(
            {'message': f'Password for user "{target_user.username}" has been reset.'},
            status=status.HTTP_200_OK
        )


class RequestPasswordResetView(APIView):
    """User requests a password reset OTP sent to their email."""

    permission_classes = [AllowAny]

    def post(self, request):
        import secrets
        from django.core.mail import send_mail
        from django.conf import settings as django_settings

        email = request.data.get('email', '').strip()
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Return success anyway to avoid email enumeration
            return Response(
                {'message': 'If an account with this email exists, an OTP has been sent.'},
                status=status.HTTP_200_OK
            )

        # Invalidate previous OTPs
        PasswordResetOTP.objects.filter(user=user, used=False).update(used=True)

        # Generate 6-char hex OTP
        otp_value = secrets.token_hex(3).upper()
        expires_at = timezone.now() + timezone.timedelta(minutes=15)

        PasswordResetOTP.objects.create(
            user=user,
            otp=otp_value,
            expires_at=expires_at,
        )

        try:
            send_mail(
                subject='SwiftPOS Password Reset OTP',
                message=f'Your password reset OTP is: {otp_value}\nThis OTP expires in 15 minutes.',
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response(
            {'message': 'If an account with this email exists, an OTP has been sent.'},
            status=status.HTTP_200_OK
        )


class ConfirmPasswordResetView(APIView):
    """User submits their OTP and new password to complete the reset."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        otp_value = request.data.get('otp', '').strip().upper()
        new_password = request.data.get('new_password', '')

        if not email or not otp_value or not new_password:
            return Response(
                {'error': 'email, otp, and new_password are all required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 8:
            return Response(
                {'error': 'new_password must be at least 8 characters.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid OTP or email.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            otp_record = PasswordResetOTP.objects.filter(
                user=user,
                otp=otp_value,
                used=False,
            ).latest('created_at')
        except PasswordResetOTP.DoesNotExist:
            return Response({'error': 'Invalid OTP or email.'}, status=status.HTTP_400_BAD_REQUEST)

        if not otp_record.is_valid():
            return Response(
                {'error': 'OTP has expired. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark OTP as used and set new password
        otp_record.used = True
        otp_record.save(update_fields=['used'])

        user.set_password(new_password)
        user.save()

        return Response(
            {'message': 'Password reset successfully. You can now log in with your new password.'},
            status=status.HTTP_200_OK
        )


class SystemSettingsView(APIView):
    """GET returns current system settings; PUT/PATCH updates (admin only)."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]

    def get(self, request):
        settings_obj = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        settings_obj = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings_obj, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        settings_obj = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings_obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
