from datetime import date as date_type
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import base64
import io
import json

import qrcode
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.authentication.permissions import IsAdminOrManager
from apps.sales.models import Sale
from .models import Payment, MobileMoneyQR, PaystackTransaction
from .serializers import PaymentSerializer, CashReconciliationSerializer
from . import paystack as paystack_service


class PaymentListView(APIView):
    """List all payments with optional filters."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Payment.objects.select_related('sale', 'sale__user').all()

        # Filter by payment method
        payment_method = request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        # Filter by specific date
        date_filter = request.query_params.get('date')
        if date_filter:
            queryset = queryset.filter(created_at__date=date_filter)

        # Cashiers see only payments for their own sales
        if request.user.role == 'cashier':
            queryset = queryset.filter(sale__user=request.user)

        queryset = queryset.order_by('-created_at')
        serializer = PaymentSerializer(queryset, many=True)

        return Response(
            {'count': queryset.count(), 'results': serializer.data},
            status=status.HTTP_200_OK
        )


class DailyCashReconciliationView(APIView):
    """Daily cash reconciliation report — expected cash vs. payment breakdown."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        date_str = request.query_params.get('date')
        if date_str:
            report_date = parse_date(date_str)
            if not report_date:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            report_date = date_type.today()

        # Get completed sales for the day
        sales_qs = Sale.objects.filter(
            sale_date__date=report_date,
            status='completed',
        )

        # Payment breakdown
        payment_summary = Payment.objects.filter(
            sale__sale_date__date=report_date,
            sale__status='completed',
        ).values('payment_method').annotate(
            count=Count('payment_id'),
            total=Sum('amount'),
        )

        payment_data = {row['payment_method']: row for row in payment_summary}

        cash_data = payment_data.get('cash', {'count': 0, 'total': Decimal('0.00')})
        mobile_data = payment_data.get('mobile_money', {'count': 0, 'total': Decimal('0.00')})
        card_data = payment_data.get('card', {'count': 0, 'total': Decimal('0.00')})

        # Refunds
        refunded_sales = Sale.objects.filter(
            sale_date__date=report_date,
            status='refunded',
        ).aggregate(
            count=Count('sale_id'),
            total=Sum('total_amount'),
        )

        total_sales = sales_qs.aggregate(
            count=Count('sale_id'),
            total=Sum('total_amount'),
        )

        data = {
            'date': report_date,
            'expected_cash': cash_data.get('total') or Decimal('0.00'),
            'total_sales_count': total_sales.get('count') or 0,
            'total_sales_amount': total_sales.get('total') or Decimal('0.00'),
            'cash_sales_count': cash_data.get('count') or 0,
            'mobile_money_count': mobile_data.get('count') or 0,
            'mobile_money_amount': mobile_data.get('total') or Decimal('0.00'),
            'card_count': card_data.get('count') or 0,
            'card_amount': card_data.get('total') or Decimal('0.00'),
            'refunds_count': refunded_sales.get('count') or 0,
            'refunds_amount': refunded_sales.get('total') or Decimal('0.00'),
        }

        serializer = CashReconciliationSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GenerateMoMoQRView(APIView):
    """Generate a Mobile Money QR code for a sale."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sale_id = request.data.get('sale_id')
        try:
            sale = Sale.objects.get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        merchant_id = getattr(settings, 'MOMO_MERCHANT_ID', 'SWIFTPOS-MERCHANT-001')
        qr_data = json.dumps({
            'merchant_id': merchant_id,
            'sale_id': sale_id,
            'amount': str(sale.total_amount),
            'currency': 'GHS',
        })

        # Generate QR image as base64
        img = qrcode.make(qr_data)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        momo_qr, _ = MobileMoneyQR.objects.update_or_create(
            sale=sale,
            defaults={
                'qr_code_data': qr_data,
                'qr_code_image_b64': img_b64,
                'merchant_id': merchant_id,
                'amount': sale.total_amount,
                'status': 'pending',
                'expires_at': timezone.now() + timedelta(minutes=15),
            }
        )

        return Response({
            'sale_id': sale_id,
            'amount': str(sale.total_amount),
            'qr_code_b64': img_b64,
            'merchant_id': merchant_id,
            'expires_at': momo_qr.expires_at,
            'status': momo_qr.status,
        })


class MoMoStatusView(APIView):
    """Poll MoMo payment status for a sale."""
    permission_classes = [IsAuthenticated]

    def get(self, request, sale_id):
        try:
            momo_qr = MobileMoneyQR.objects.get(sale_id=sale_id)
        except MobileMoneyQR.DoesNotExist:
            return Response({'error': 'No QR code found for this sale.'}, status=status.HTTP_404_NOT_FOUND)

        if momo_qr.status == 'pending' and timezone.now() > momo_qr.expires_at:
            momo_qr.status = 'expired'
            momo_qr.save(update_fields=['status'])

        return Response({
            'sale_id': sale_id,
            'status': momo_qr.status,
            'amount': str(momo_qr.amount),
            'transaction_ref': momo_qr.transaction_ref,
            'expires_at': momo_qr.expires_at,
        })


class MoMoConfirmView(APIView):
    """Confirm a MoMo payment (called by manager or webhook)."""
    permission_classes = [IsAdminOrManager]

    def post(self, request, sale_id):
        try:
            momo_qr = MobileMoneyQR.objects.get(sale_id=sale_id)
        except MobileMoneyQR.DoesNotExist:
            return Response({'error': 'No QR code found for this sale.'}, status=status.HTTP_404_NOT_FOUND)

        if momo_qr.status != 'pending':
            return Response({'error': f'Payment is already {momo_qr.status}.'}, status=status.HTTP_400_BAD_REQUEST)

        transaction_ref = request.data.get('transaction_ref', '')
        momo_qr.status = 'confirmed'
        momo_qr.transaction_ref = transaction_ref
        momo_qr.save(update_fields=['status', 'transaction_ref'])

        # Update or create the payment record
        Payment.objects.update_or_create(
            sale=momo_qr.sale,
            payment_method='mobile_money',
            defaults={'amount': momo_qr.amount, 'reference_number': transaction_ref},
        )

        return Response({'message': 'Payment confirmed.', 'transaction_ref': transaction_ref})


class InitiateMoMoPaymentView(APIView):
    """
    Initiate a real Mobile Money payment via Paystack.

    POST body:
      sale_id   - int
      phone     - customer's MoMo number (e.g. 0241234567)
      provider  - 'mtn' | 'vodafone' | 'airteltigo'
      email     - customer email (optional, defaults to generic)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sale_id = request.data.get('sale_id')
        phone = request.data.get('phone', '').strip()
        provider = request.data.get('provider', '').strip().lower()
        email = request.data.get('email', '').strip() or 'customer@swiftpos.com'

        if not sale_id or not phone or not provider:
            return Response(
                {'error': 'sale_id, phone, and provider are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if provider not in ('mtn', 'vodafone', 'airteltigo', 'tigo'):
            return Response(
                {'error': "provider must be 'mtn', 'vodafone', or 'airteltigo'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sale = Sale.objects.get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Prevent duplicate charges for the same sale
        existing = PaystackTransaction.objects.filter(
            sale=sale, status='success'
        ).first()
        if existing:
            return Response(
                {'error': 'This sale already has a successful payment.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reference = PaystackTransaction.generate_reference(sale_id)

        result = paystack_service.initiate_momo_charge(
            email=email,
            amount_ghs=sale.total_amount,
            phone=phone,
            provider=provider,
            reference=reference,
            metadata={'sale_id': sale_id, 'cashier': request.user.full_name},
        )

        paystack_status = result.get('data', {}).get('status', '')

        # Paystack returns status:false for both API errors and declined charges.
        # Treat "failed" data status as a payment decline (400), not a server error (502).
        if not result.get('status'):
            if paystack_status == 'failed':
                charge_msg = result.get('data', {}).get('message') or result.get('message', 'Payment declined.')
                return Response({'error': charge_msg}, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {'error': result.get('message', 'Paystack error.')},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        PaystackTransaction.objects.update_or_create(
            sale=sale,
            defaults={
                'reference': reference,
                'amount': sale.total_amount,
                'phone': phone,
                'provider': provider,
                'customer_email': email,
                'status': paystack_status if paystack_status in ('success', 'failed') else 'pay_offline',
                'paystack_status': paystack_status,
            },
        )

        # If Paystack returned immediate success (rare), record payment now
        if paystack_status == 'success':
            Payment.objects.update_or_create(
                sale=sale,
                payment_method='mobile_money',
                defaults={'amount': sale.total_amount, 'reference_number': reference},
            )

        return Response({
            'reference': reference,
            'status': paystack_status,
            'message': result.get('data', {}).get('display_text') or (
                'Approve the payment prompt on your phone.' if paystack_status != 'success'
                else 'Payment successful.'
            ),
            'amount': str(sale.total_amount),
        })


class SubmitMoMoOTPView(APIView):
    """
    Submit OTP for Vodafone Cash charges.
    Paystack returns status='send_otp' for Vodafone Cash — the customer receives
    an OTP via SMS which must be forwarded here to complete the charge.

    POST body: { "reference": "SWFTPS-xxx", "otp": "123456" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reference = request.data.get('reference', '').strip()
        otp = request.data.get('otp', '').strip()

        if not reference or not otp:
            return Response(
                {'error': 'reference and otp are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = paystack_service.submit_otp(otp=otp, reference=reference)

        if not result.get('status'):
            return Response(
                {'error': result.get('message', 'OTP submission failed.')},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        paystack_status = result.get('data', {}).get('status', '')

        # Update transaction record
        try:
            txn = PaystackTransaction.objects.select_related('sale').get(reference=reference)
            txn.paystack_status = paystack_status
            if paystack_status == 'success':
                txn.status = 'success'
                txn.save(update_fields=['status', 'paystack_status', 'updated_at'])
                Payment.objects.update_or_create(
                    sale=txn.sale,
                    payment_method='mobile_money',
                    defaults={'amount': txn.amount, 'reference_number': reference},
                )
            else:
                txn.save(update_fields=['paystack_status', 'updated_at'])
        except PaystackTransaction.DoesNotExist:
            pass

        return Response({
            'status': paystack_status,
            'message': result.get('data', {}).get('display_text') or (
                'Payment successful.' if paystack_status == 'success'
                else 'OTP submitted — awaiting confirmation.'
            ),
        })


class VerifyPaystackPaymentView(APIView):
    """
    Manually verify a Paystack payment by reference.
    Use this as a fallback if the webhook is not yet set up.

    POST body: { "reference": "SWFTPS-xxx-yyy" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reference = request.data.get('reference', '').strip()
        if not reference:
            return Response({'error': 'reference is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            txn = PaystackTransaction.objects.select_related('sale').get(reference=reference)
        except PaystackTransaction.DoesNotExist:
            return Response({'error': 'Transaction not found.'}, status=status.HTTP_404_NOT_FOUND)

        if txn.status == 'success':
            return Response({'status': 'success', 'message': 'Already confirmed.'})

        result = paystack_service.verify_transaction(reference)

        if not result.get('status'):
            return Response(
                {'error': result.get('message', 'Verification failed.')},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        paystack_status = result.get('data', {}).get('status', '')

        if paystack_status == 'success':
            txn.status = 'success'
            txn.paystack_status = paystack_status
            txn.save(update_fields=['status', 'paystack_status', 'updated_at'])

            Payment.objects.update_or_create(
                sale=txn.sale,
                payment_method='mobile_money',
                defaults={'amount': txn.amount, 'reference_number': reference},
            )
            return Response({'status': 'success', 'message': 'Payment verified and confirmed.'})

        txn.paystack_status = paystack_status
        txn.save(update_fields=['paystack_status', 'updated_at'])
        return Response({'status': paystack_status, 'message': 'Payment not yet completed.'})


@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(APIView):
    """
    Paystack webhook endpoint — auto-confirms MoMo payments.
    Register this URL in your Paystack dashboard under Settings → API Keys → Webhook URL.
    No authentication (Paystack calls this directly); validated by HMAC-SHA512 signature.
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        signature = request.headers.get('X-Paystack-Signature', '')
        if not paystack_service.validate_webhook_signature(request.body, signature):
            return Response({'error': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON.'}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get('event')
        data = payload.get('data', {})

        if event == 'charge.success':
            reference = data.get('reference', '')
            try:
                txn = PaystackTransaction.objects.select_related('sale').get(reference=reference)
            except PaystackTransaction.DoesNotExist:
                # Not our transaction — acknowledge and ignore
                return Response({'status': 'ok'})

            if txn.status != 'success':
                txn.status = 'success'
                txn.paystack_status = 'success'
                txn.save(update_fields=['status', 'paystack_status', 'updated_at'])

                Payment.objects.update_or_create(
                    sale=txn.sale,
                    payment_method='mobile_money',
                    defaults={'amount': txn.amount, 'reference_number': reference},
                )

        return Response({'status': 'ok'})
