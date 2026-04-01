from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from apps.inventory.models import StockMovement
from apps.products.models import Product
from .models import Sale, SaleItem, TransactionLog
from .serializers import (
    SaleCreateSerializer,
    SaleListSerializer,
    SaleSerializer,
)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class SaleListView(APIView):
    """List all sales with optional date and user filters."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Cashiers can only see their own sales; managers/admins see all
        if user.role == 'cashier':
            queryset = Sale.objects.filter(user=user)
        else:
            queryset = Sale.objects.all()

        # Date filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(sale_date__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(sale_date__date__lte=end_date)

        # Filter by specific date
        date = request.query_params.get('date')
        if date:
            queryset = queryset.filter(sale_date__date=date)

        # Filter by payment method
        payment_method = request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        # Filter by status
        sale_status = request.query_params.get('status')
        if sale_status:
            queryset = queryset.filter(status=sale_status)

        # Filter by cashier (manager/admin only)
        cashier_id = request.query_params.get('cashier_id')
        if cashier_id and user.role in ['admin', 'manager']:
            queryset = queryset.filter(user_id=cashier_id)

        queryset = queryset.select_related('user', 'customer').prefetch_related('items').order_by('-sale_date')
        serializer = SaleListSerializer(queryset, many=True)

        return Response(
            {'count': queryset.count(), 'results': serializer.data},
            status=status.HTTP_200_OK
        )


class SaleCreateView(APIView):
    """Create a new sale transaction atomically."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = SaleCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        items_data = data['items']
        payment_method = data['payment_method']
        tax_rate = data.get('tax_rate', Decimal('0.00'))
        global_discount_amount = data.get('discount_amount', Decimal('0.00'))
        notes = data.get('notes', '')
        customer_id = data.get('customer_id')

        # Lock and fetch products to prevent race conditions
        product_ids = [item['product_id'] for item in items_data]
        products = {
            p.product_id: p
            for p in Product.objects.select_for_update().filter(product_id__in=product_ids)
        }

        # Final stock validation inside transaction
        for item_data in items_data:
            product = products[item_data['product_id']]
            if product.quantity < item_data['quantity']:
                raise Exception(
                    f'Insufficient stock for "{product.product_name}". '
                    f'Available: {product.quantity}, Requested: {item_data["quantity"]}'
                )

        # Calculate totals
        subtotal = Decimal('0.00')
        item_details = []

        for item_data in items_data:
            product = products[item_data['product_id']]
            quantity = item_data['quantity']
            discount_pct = item_data.get('discount_pct', Decimal('0.00'))
            unit_price = product.price
            discount_multiplier = 1 - (discount_pct / 100)
            line_total = unit_price * quantity * discount_multiplier
            subtotal += line_total
            item_details.append({
                'product': product,
                'quantity': quantity,
                'unit_price': unit_price,
                'discount_pct': discount_pct,
                'line_total': line_total,
            })

        # Apply global discount
        effective_subtotal = subtotal - global_discount_amount
        if effective_subtotal < 0:
            effective_subtotal = Decimal('0.00')

        # Calculate tax
        tax_amount = effective_subtotal * (tax_rate / 100)
        total_amount = effective_subtotal + tax_amount

        # Get customer
        customer = None
        if customer_id:
            from apps.customers.models import Customer
            try:
                customer = Customer.objects.get(customer_id=customer_id)
            except Customer.DoesNotExist:
                pass

        # Create the Sale record
        sale = Sale.objects.create(
            user=request.user,
            customer=customer,
            subtotal=subtotal,
            discount_amount=global_discount_amount,
            tax_amount=tax_amount,
            tax_rate=tax_rate,
            total_amount=total_amount,
            payment_method=payment_method,
            status='completed',
            notes=notes,
        )

        # Create SaleItems and update inventory
        for item_detail in item_details:
            product = item_detail['product']
            quantity = item_detail['quantity']

            # Create sale item
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                unit_price=item_detail['unit_price'],
                discount_pct=item_detail['discount_pct'],
                line_total=item_detail['line_total'],
            )

            # Decrement inventory
            quantity_before = product.quantity
            quantity_after = quantity_before - quantity
            product.quantity = quantity_after
            product.save(update_fields=['quantity'])

            # Create stock movement record
            StockMovement.objects.create(
                product=product,
                movement_type='sale',
                quantity_change=-quantity,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                reason=f'Sale #{sale.sale_id}',
                reference_id=str(sale.sale_id),
                user=request.user,
            )

        # Update customer loyalty points and spending
        if customer:
            customer.update_spending(total_amount)

        # Log the transaction
        TransactionLog.objects.create(
            user=request.user,
            action='sale_created',
            entity_type='sale',
            entity_id=str(sale.sale_id),
            details={
                'total_amount': str(total_amount),
                'payment_method': payment_method,
                'item_count': len(item_details),
                'customer_id': customer_id,
            },
            ip_address=get_client_ip(request),
        )

        # Create payment record(s)
        from apps.payments.models import Payment
        if payment_method == 'split':
            payments_data = request.data.get('payments', [])
            if payments_data:
                for p_data in payments_data:
                    p_amount = Decimal(str(p_data.get('amount', 0)))
                    p_method = p_data.get('method', 'cash')
                    p_tendered = p_data.get('amount_tendered')
                    p_change = None
                    if p_method == 'cash' and p_tendered is not None:
                        p_tendered = Decimal(str(p_tendered))
                        p_change = max(Decimal('0.00'), p_tendered - p_amount)
                    else:
                        p_tendered = None
                    Payment.objects.create(
                        sale=sale,
                        payment_method=p_method,
                        amount=p_amount,
                        amount_tendered=p_tendered,
                        change_due=p_change,
                    )
            else:
                Payment.objects.create(
                    sale=sale,
                    payment_method=payment_method,
                    amount=total_amount,
                )
        else:
            amount_tendered = data.get('amount_tendered') or request.data.get('amount_tendered')
            change_due = None
            if payment_method == 'cash' and amount_tendered is not None:
                amount_tendered = Decimal(str(amount_tendered))
                change_due = max(Decimal('0.00'), amount_tendered - total_amount)
            else:
                amount_tendered = None
            Payment.objects.create(
                sale=sale,
                payment_method=payment_method,
                amount=total_amount,
                amount_tendered=amount_tendered,
                change_due=change_due,
            )

        # Attempt to send receipt email to customer (non-blocking)
        if customer and customer.email:
            try:
                from django.core.mail import send_mail
                from django.conf import settings as django_settings
                send_mail(
                    subject=f'Receipt for Sale #{sale.sale_id}',
                    message=(
                        f'Dear {customer.full_name},\n\n'
                        f'Thank you for your purchase!\n'
                        f'Sale #{sale.sale_id}\n'
                        f'Total: {total_amount}\n'
                        f'Payment method: {payment_method}\n\n'
                        f'We appreciate your business!'
                    ),
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[customer.email],
                    fail_silently=True,
                )
            except Exception:
                pass

        return Response(
            SaleSerializer(sale).data,
            status=status.HTTP_201_CREATED
        )


class SaleDetailView(APIView):
    """Retrieve a specific sale with all its items."""

    permission_classes = [IsAuthenticated]

    def get(self, request, sale_id):
        try:
            sale = Sale.objects.select_related(
                'user', 'customer'
            ).prefetch_related('items__product').get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Cashiers can only view their own sales
        if request.user.role == 'cashier' and sale.user != request.user:
            return Response(
                {'error': 'You do not have permission to view this sale.'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response(SaleSerializer(sale).data, status=status.HTTP_200_OK)


class SaleVoidView(APIView):
    """Void a sale and restore inventory. Manager/Admin only."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    @transaction.atomic
    def post(self, request, sale_id):
        try:
            sale = Sale.objects.select_related('customer').prefetch_related(
                'items__product'
            ).get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        if sale.status != 'completed':
            return Response(
                {'error': f'Cannot void a sale with status "{sale.status}".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', 'Voided by manager')

        # Restore stock for each item
        for item in sale.items.all():
            if item.product:
                product = Product.objects.select_for_update().get(product_id=item.product.product_id)
                quantity_before = product.quantity
                quantity_after = quantity_before + item.quantity
                product.quantity = quantity_after
                product.save(update_fields=['quantity'])

                StockMovement.objects.create(
                    product=product,
                    movement_type='return',
                    quantity_change=item.quantity,
                    quantity_before=quantity_before,
                    quantity_after=quantity_after,
                    reason=f'Sale #{sale.sale_id} voided: {reason}',
                    reference_id=str(sale.sale_id),
                    user=request.user,
                )

        # Reverse customer loyalty points
        if sale.customer:
            customer = sale.customer
            points_to_remove = int(sale.total_amount)
            customer.loyalty_points = max(0, customer.loyalty_points - points_to_remove)
            customer.total_spent = max(Decimal('0.00'), customer.total_spent - sale.total_amount)
            customer.save(update_fields=['loyalty_points', 'total_spent'])

        # Update sale status
        sale.status = 'voided'
        sale.notes = f'{sale.notes or ""}\nVoided: {reason}'.strip()
        sale.save(update_fields=['status', 'notes'])

        # Log the action
        TransactionLog.objects.create(
            user=request.user,
            action='sale_voided',
            entity_type='sale',
            entity_id=str(sale.sale_id),
            details={'reason': reason, 'total_amount': str(sale.total_amount)},
            ip_address=get_client_ip(request),
        )

        return Response(
            {
                'message': f'Sale #{sale.sale_id} has been voided.',
                'sale': SaleSerializer(sale).data,
            },
            status=status.HTTP_200_OK
        )


class SaleRefundView(APIView):
    """Refund a sale and restore inventory. Manager/Admin only."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    @transaction.atomic
    def post(self, request, sale_id):
        try:
            sale = Sale.objects.select_related('customer').prefetch_related(
                'items__product'
            ).get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        if sale.status != 'completed':
            return Response(
                {'error': f'Cannot refund a sale with status "{sale.status}".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', 'Customer refund')

        # Restore stock for each item
        for item in sale.items.all():
            if item.product:
                product = Product.objects.select_for_update().get(product_id=item.product.product_id)
                quantity_before = product.quantity
                quantity_after = quantity_before + item.quantity
                product.quantity = quantity_after
                product.save(update_fields=['quantity'])

                StockMovement.objects.create(
                    product=product,
                    movement_type='return',
                    quantity_change=item.quantity,
                    quantity_before=quantity_before,
                    quantity_after=quantity_after,
                    reason=f'Sale #{sale.sale_id} refunded: {reason}',
                    reference_id=str(sale.sale_id),
                    user=request.user,
                )

        # Reverse customer loyalty points
        if sale.customer:
            customer = sale.customer
            points_to_remove = int(sale.total_amount)
            customer.loyalty_points = max(0, customer.loyalty_points - points_to_remove)
            customer.total_spent = max(Decimal('0.00'), customer.total_spent - sale.total_amount)
            customer.save(update_fields=['loyalty_points', 'total_spent'])

        # Update sale status
        sale.status = 'refunded'
        sale.notes = f'{sale.notes or ""}\nRefunded: {reason}'.strip()
        sale.save(update_fields=['status', 'notes'])

        # Log the action
        TransactionLog.objects.create(
            user=request.user,
            action='sale_refunded',
            entity_type='sale',
            entity_id=str(sale.sale_id),
            details={'reason': reason, 'total_amount': str(sale.total_amount)},
            ip_address=get_client_ip(request),
        )

        return Response(
            {
                'message': f'Sale #{sale.sale_id} has been refunded.',
                'sale': SaleSerializer(sale).data,
            },
            status=status.HTTP_200_OK
        )


class CustomerDisplayView(APIView):
    """Public endpoint — customer-facing display screen polls this."""
    permission_classes = []

    def get(self, request, sale_id):
        try:
            sale = Sale.objects.select_related('user').prefetch_related('items__product').get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        items = [
            {
                'product_name': item.product.product_name if item.product else 'Unknown',
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'line_total': str(item.line_total),
            }
            for item in sale.items.all()
        ]

        return Response({
            'sale_id': sale.sale_id,
            'cashier': sale.user.full_name,
            'items': items,
            'subtotal': str(sale.subtotal),
            'discount': str(sale.discount_amount),
            'tax': str(sale.tax_amount),
            'total': str(sale.total_amount),
            'status': sale.status,
            'store_name': 'SwiftPOS',
        })


class ActiveSaleDisplayView(APIView):
    """Returns the most recent open/completed sale for a cashier (for display screen)."""
    permission_classes = []

    def get(self, request, cashier_id):
        sale = Sale.objects.filter(
            user_id=cashier_id,
            status='completed',
        ).order_by('-sale_date').first()

        if not sale:
            return Response({'message': 'No recent sale found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'sale_id': sale.sale_id,
            'total': str(sale.total_amount),
            'status': sale.status,
            'sale_date': sale.sale_date,
        })


class SaleHoldView(APIView):
    """Put a completed sale on hold so it can be resumed later."""

    permission_classes = [IsAuthenticated]

    def post(self, request, sale_id):
        try:
            sale = Sale.objects.get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'cashier' and sale.user != request.user:
            return Response(
                {'error': 'You do not have permission to hold this sale.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if sale.status != 'completed':
            return Response(
                {'error': f'Cannot hold a sale with status "{sale.status}".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        sale.status = 'held'
        sale.save(update_fields=['status'])

        TransactionLog.objects.create(
            user=request.user,
            action='sale_held',
            entity_type='sale',
            entity_id=str(sale.sale_id),
            details={'total_amount': str(sale.total_amount)},
            ip_address=get_client_ip(request),
        )

        return Response(
            {'message': f'Sale #{sale.sale_id} is now on hold.', 'sale': SaleSerializer(sale).data},
            status=status.HTTP_200_OK
        )


class SaleResumeView(APIView):
    """Resume a held sale (set back to completed)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, sale_id):
        try:
            sale = Sale.objects.get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'cashier' and sale.user != request.user:
            return Response(
                {'error': 'You do not have permission to resume this sale.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if sale.status != 'held':
            return Response(
                {'error': f'Cannot resume a sale with status "{sale.status}". Only held sales can be resumed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        sale.status = 'completed'
        sale.save(update_fields=['status'])

        TransactionLog.objects.create(
            user=request.user,
            action='sale_resumed',
            entity_type='sale',
            entity_id=str(sale.sale_id),
            details={'total_amount': str(sale.total_amount)},
            ip_address=get_client_ip(request),
        )

        return Response(
            {'message': f'Sale #{sale.sale_id} has been resumed.', 'sale': SaleSerializer(sale).data},
            status=status.HTTP_200_OK
        )
