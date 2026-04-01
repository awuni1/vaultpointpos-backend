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

from apps.authentication.permissions import IsAdminOrManager
from apps.sales.models import Sale
from .models import Payment, MobileMoneyQR
from .serializers import PaymentSerializer, CashReconciliationSerializer


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
