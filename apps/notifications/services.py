"""
Notification services for SwiftPOS.
Email uses Django's built-in send_mail (console backend in dev).
SMS uses a stub — replace with Twilio in production.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import NotificationLog

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send(recipient_email: str, subject: str, message: str, notification_type: str = 'receipt_email'):
        log = NotificationLog.objects.create(
            notification_type=notification_type,
            recipient=recipient_email,
            message=message,
            status='pending',
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.save(update_fields=['status', 'sent_at'])
            return True
        except Exception as exc:
            log.status = 'failed'
            log.error_message = str(exc)
            log.save(update_fields=['status', 'error_message'])
            logger.error('Email failed to %s: %s', recipient_email, exc)
            return False


class SMSService:
    """
    Stub SMS service. Replace the _send_via_twilio method with real Twilio logic.
    Install twilio package and set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER in .env.
    """
    @staticmethod
    def send(recipient_phone: str, message: str, notification_type: str = 'receipt_sms'):
        log = NotificationLog.objects.create(
            notification_type=notification_type,
            recipient=recipient_phone,
            message=message,
            status='pending',
        )
        try:
            SMSService._send_via_stub(recipient_phone, message)
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.save(update_fields=['status', 'sent_at'])
            return True
        except Exception as exc:
            log.status = 'failed'
            log.error_message = str(exc)
            log.save(update_fields=['status', 'error_message'])
            logger.error('SMS failed to %s: %s', recipient_phone, exc)
            return False

    @staticmethod
    def _send_via_stub(phone: str, message: str):
        # In production, replace with:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # client.messages.create(to=phone, from_=settings.TWILIO_FROM_NUMBER, body=message)
        logger.info('[SMS STUB] To: %s | Message: %s', phone, message)
