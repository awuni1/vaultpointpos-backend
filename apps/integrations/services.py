"""WebhookService — dispatch events to registered webhook URLs."""
import hashlib
import hmac
import json
import logging

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


class WebhookService:
    @staticmethod
    def dispatch(event_type: str, payload: dict):
        from .models import Webhook, WebhookDelivery

        webhooks = Webhook.objects.filter(is_active=True)
        for webhook in webhooks:
            if event_type not in webhook.events:
                continue

            delivery = WebhookDelivery.objects.create(
                webhook=webhook,
                event_type=event_type,
                payload=payload,
                status='pending',
            )

            try:
                body = json.dumps(payload)
                signature = hmac.new(
                    webhook.secret.encode('utf-8'),
                    body.encode('utf-8'),
                    hashlib.sha256,
                ).hexdigest()

                response = requests.post(
                    webhook.url,
                    data=body,
                    headers={
                        'Content-Type': 'application/json',
                        'X-SwiftPOS-Signature': f'sha256={signature}',
                        'X-SwiftPOS-Event': event_type,
                    },
                    timeout=10,
                )
                delivery.response_code = response.status_code
                delivery.status = 'success' if response.ok else 'failed'
                delivery.delivered_at = timezone.now()
            except Exception as exc:
                delivery.status = 'failed'
                delivery.response_code = None
                logger.error('Webhook delivery failed for %s: %s', webhook.url, exc)

            delivery.save()
