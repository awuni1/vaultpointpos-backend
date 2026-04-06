"""Paystack API service for Mobile Money payments."""

import hashlib
import hmac
import requests
from django.conf import settings

PAYSTACK_BASE_URL = 'https://api.paystack.co'

PROVIDER_MAP = {
    'mtn': 'mtn',
    'vodafone': 'vod',
    'airteltigo': 'tgo',
    'tigo': 'tgo',
}


def _headers():
    return {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }


def _normalize_ghana_phone(phone: str) -> str:
    """Convert local Ghana number to international format Paystack expects."""
    phone = phone.strip().replace(' ', '').replace('-', '')
    if phone.startswith('0') and len(phone) == 10:
        return '233' + phone[1:]
    if phone.startswith('+233'):
        return phone[1:]  # strip the +
    return phone


def initiate_momo_charge(email, amount_ghs, phone, provider, reference, metadata=None):
    """
    Initiate a mobile money charge.

    provider: 'mtn' | 'vodafone' | 'airteltigo'
    amount_ghs: amount in GHS (converted to pesewas internally)
    Returns Paystack response dict.
    """
    amount_pesewas = int(float(amount_ghs) * 100)
    normalized_phone = _normalize_ghana_phone(phone)

    payload = {
        'email': email,
        'amount': amount_pesewas,
        'currency': 'GHS',
        'reference': reference,
        'mobile_money': {
            'phone': normalized_phone,
            'provider': PROVIDER_MAP.get(provider, provider),
        },
    }
    if metadata:
        payload['metadata'] = metadata

    response = requests.post(
        f'{PAYSTACK_BASE_URL}/charge',
        json=payload,
        headers=_headers(),
        timeout=30,
    )
    return response.json()


def submit_otp(otp: str, reference: str):
    """Submit OTP for Vodafone Cash charges that return send_otp status."""
    response = requests.post(
        f'{PAYSTACK_BASE_URL}/charge/submit_otp',
        json={'otp': otp, 'reference': reference},
        headers=_headers(),
        timeout=30,
    )
    return response.json()


def verify_transaction(reference):
    """Verify a Paystack transaction by reference."""
    response = requests.get(
        f'{PAYSTACK_BASE_URL}/transaction/verify/{reference}',
        headers=_headers(),
        timeout=30,
    )
    return response.json()


def validate_webhook_signature(payload_bytes, signature):
    """Validate Paystack webhook HMAC-SHA512 signature."""
    secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    expected = hmac.new(secret, payload_bytes, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)
