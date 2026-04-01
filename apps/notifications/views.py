from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from apps.products.models import Product
from apps.sales.models import Sale
from .models import NotificationLog
from .serializers import (
    NotificationLogSerializer, SendReceiptEmailSerializer, SendReceiptSMSSerializer
)
from .services import EmailService, SMSService


class SendReceiptEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SendReceiptEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            sale = Sale.objects.prefetch_related('items__product').get(sale_id=serializer.validated_data['sale_id'])
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        lines = '\n'.join(
            f'  {item.product.product_name} x{item.quantity} @ {item.unit_price} = {item.line_total}'
            for item in sale.items.all()
        )
        message = (
            f'Receipt for Sale #{sale.sale_id}\n'
            f'Date: {sale.sale_date:%Y-%m-%d %H:%M}\n\n'
            f'Items:\n{lines}\n\n'
            f'Subtotal: {sale.subtotal}\n'
            f'Discount: {sale.discount_amount}\n'
            f'Tax: {sale.tax_amount}\n'
            f'TOTAL: {sale.total_amount}\n\n'
            f'Payment: {sale.payment_method}\n\n'
            f'Thank you for shopping with us!'
        )
        success = EmailService.send(
            recipient_email=serializer.validated_data['email'],
            subject=f'SwiftPOS Receipt #{sale.sale_id}',
            message=message,
            notification_type='receipt_email',
        )
        return Response({'success': success, 'message': 'Receipt email sent.' if success else 'Failed to send email.'})


class SendReceiptSMSView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SendReceiptSMSSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            sale = Sale.objects.get(sale_id=serializer.validated_data['sale_id'])
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        message = (
            f'SwiftPOS Receipt #{sale.sale_id} | '
            f'Total: GHS {sale.total_amount} | '
            f'{sale.sale_date:%d/%m/%Y %H:%M} | '
            f'Thank you!'
        )
        success = SMSService.send(
            recipient_phone=serializer.validated_data['phone'],
            message=message,
            notification_type='receipt_sms',
        )
        return Response({'success': success})


class LowStockAlertView(APIView):
    permission_classes = [IsAdminOrManager]

    def post(self, request):
        from django.db.models import F
        low_stock = Product.objects.filter(is_active=True, quantity__lte=F('reorder_level'))
        if not low_stock.exists():
            return Response({'message': 'No low stock items.'})

        lines = '\n'.join(
            f'  {p.product_name}: {p.quantity} left (reorder at {p.reorder_level})'
            for p in low_stock
        )
        message = f'SwiftPOS Low Stock Alert\n\nThe following products need restocking:\n{lines}'
        manager_email = getattr(settings, 'MANAGER_EMAIL', '')
        manager_phone = getattr(settings, 'MANAGER_PHONE', '')

        results = {}
        if manager_email:
            results['email'] = EmailService.send(manager_email, 'SwiftPOS Low Stock Alert', message, 'low_stock')
        if manager_phone:
            short_msg = f'SwiftPOS: {low_stock.count()} items low on stock. Check dashboard.'
            results['sms'] = SMSService.send(manager_phone, short_msg, 'low_stock')

        return Response({'message': 'Alert sent.', 'results': results, 'low_stock_count': low_stock.count()})


class DailySummaryEmailView(APIView):
    permission_classes = [IsAdminOrManager]

    def post(self, request):
        date_str = request.data.get('date', timezone.now().date().isoformat())
        sales = Sale.objects.filter(sale_date__date=date_str, status='completed')
        total = sales.aggregate(t=Sum('total_amount'))['t'] or 0

        message = (
            f'SwiftPOS Daily Summary — {date_str}\n\n'
            f'Total Revenue: GHS {total}\n'
            f'Transactions: {sales.count()}\n'
            f'Average Sale: GHS {(total / sales.count()) if sales.count() else 0:.2f}\n\n'
            f'Generated at {timezone.now():%Y-%m-%d %H:%M}'
        )
        email = request.data.get('email', getattr(settings, 'MANAGER_EMAIL', ''))
        if not email:
            return Response({'error': 'No manager email configured.'}, status=status.HTTP_400_BAD_REQUEST)

        success = EmailService.send(email, f'SwiftPOS Daily Summary — {date_str}', message, 'daily_summary')
        return Response({'success': success})


class NotificationLogListView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        logs = NotificationLog.objects.all()
        ntype = request.query_params.get('type')
        if ntype:
            logs = logs.filter(notification_type=ntype)
        status_filter = request.query_params.get('status')
        if status_filter:
            logs = logs.filter(status=status_filter)
        return Response(NotificationLogSerializer(logs[:100], many=True).data)
