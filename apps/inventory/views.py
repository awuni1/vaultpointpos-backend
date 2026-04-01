from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from apps.products.models import Product
from .models import StockMovement, SupplierDelivery
from .serializers import (
    InventoryItemSerializer,
    ReceiveStockSerializer,
    StockAdjustmentSerializer,
    StockMovementSerializer,
    SupplierDeliverySerializer,
)


class InventoryListView(APIView):
    """List all products with their current stock levels."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Product.objects.select_related('category').all()

        # Filter by active status
        show_inactive = request.query_params.get('show_inactive', 'false').lower() == 'true'
        if not show_inactive:
            queryset = queryset.filter(is_active=True)

        # Filter low stock only
        low_stock_only = request.query_params.get('low_stock', 'false').lower() == 'true'
        if low_stock_only:
            queryset = queryset.filter(quantity__lte=F('reorder_level'))

        # Filter by category
        category_id = request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        serializer = InventoryItemSerializer(queryset, many=True)
        return Response(
            {
                'count': queryset.count(),
                'results': serializer.data,
            },
            status=status.HTTP_200_OK
        )


class StockAdjustmentView(APIView):
    """Manually adjust stock levels. Manager/Admin only."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    @transaction.atomic
    def post(self, request):
        serializer = StockAdjustmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product = serializer.validated_data['product']
        quantity_change = serializer.validated_data['quantity_change']
        reason = serializer.validated_data['reason']

        quantity_before = product.quantity
        quantity_after = quantity_before + quantity_change

        # Update product stock
        product.quantity = quantity_after
        product.save(update_fields=['quantity'])

        # Record the movement
        movement = StockMovement.objects.create(
            product=product,
            movement_type='adjustment',
            quantity_change=quantity_change,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reason=reason,
            user=request.user,
        )

        return Response(
            {
                'message': f'Stock adjusted successfully for "{product.product_name}".',
                'movement': StockMovementSerializer(movement).data,
                'product': {
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'quantity_before': quantity_before,
                    'quantity_after': quantity_after,
                },
            },
            status=status.HTTP_200_OK
        )


class ReceiveStockView(APIView):
    """Receive stock from a supplier delivery. Manager/Admin only."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    @transaction.atomic
    def post(self, request):
        serializer = ReceiveStockSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product = serializer.validated_data['product']
        quantity_received = serializer.validated_data['quantity_received']
        unit_cost = serializer.validated_data['unit_cost']

        quantity_before = product.quantity
        quantity_after = quantity_before + quantity_received

        # Save the delivery record
        delivery = serializer.save(user=request.user)

        # Update product stock and cost price
        product.quantity = quantity_after
        if unit_cost:
            product.cost_price = unit_cost
        product.save(update_fields=['quantity', 'cost_price'])

        # Create stock movement record
        movement = StockMovement.objects.create(
            product=product,
            movement_type='receive',
            quantity_change=quantity_received,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reason=f'Supplier delivery from {delivery.supplier_name}',
            reference_id=str(delivery.delivery_id),
            user=request.user,
        )

        return Response(
            {
                'message': f'Stock received successfully for "{product.product_name}".',
                'delivery': SupplierDeliverySerializer(delivery).data,
                'movement': StockMovementSerializer(movement).data,
                'product': {
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'quantity_before': quantity_before,
                    'quantity_after': quantity_after,
                },
            },
            status=status.HTTP_201_CREATED
        )


class StockMovementListView(APIView):
    """Audit log of all stock changes."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = StockMovement.objects.select_related('product', 'user').all()

        # Filter by product
        product_id = request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        # Filter by movement type
        movement_type = request.query_params.get('movement_type')
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)

        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        queryset = queryset.order_by('-created_at')[:200]
        serializer = StockMovementSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LowStockView(APIView):
    """List products that are at or below their reorder level."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        low_stock_products = Product.objects.select_related('category').filter(
            is_active=True,
            quantity__lte=F('reorder_level'),
        ).order_by('quantity')

        serializer = InventoryItemSerializer(low_stock_products, many=True)
        return Response(
            {
                'count': low_stock_products.count(),
                'results': serializer.data,
            },
            status=status.HTTP_200_OK
        )


class DeadStockView(APIView):
    """Return products with zero sales in the last N days (default 90)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils import timezone as tz
        from datetime import timedelta
        from apps.sales.models import SaleItem

        try:
            days = int(request.query_params.get('days', 90))
        except (ValueError, TypeError):
            days = 90

        cutoff = tz.now() - timedelta(days=days)

        # Products that had at least one sale in the period
        sold_product_ids = SaleItem.objects.filter(
            sale__sale_date__gte=cutoff,
            sale__status='completed',
        ).values_list('product_id', flat=True).distinct()

        dead_stock = Product.objects.select_related('category').filter(
            is_active=True,
            quantity__gt=0,
        ).exclude(product_id__in=sold_product_ids).order_by('-quantity')

        serializer = InventoryItemSerializer(dead_stock, many=True)
        return Response(
            {
                'days': days,
                'count': dead_stock.count(),
                'results': serializer.data,
            },
            status=status.HTTP_200_OK
        )


class InventoryExportView(APIView):
    """Export full inventory as CSV or PDF."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        import csv
        import io as _io
        from django.http import HttpResponse

        fmt = request.query_params.get('format', 'csv').lower()
        products = Product.objects.select_related('category').filter(is_active=True).order_by('product_name')

        if fmt == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Name', 'Category', 'Price', 'Cost Price', 'Quantity', 'Reorder Level', 'Inventory Value', 'Cost Value'])
            for p in products:
                inv_value = float(p.price) * p.quantity
                cost_value = float(p.cost_price) * p.quantity if p.cost_price else 0
                writer.writerow([
                    p.product_id,
                    p.product_name,
                    p.category.name if p.category else '',
                    float(p.price),
                    float(p.cost_price) if p.cost_price else '',
                    p.quantity,
                    p.reorder_level,
                    round(inv_value, 2),
                    round(cost_value, 2),
                ])
            return response

        elif fmt == 'pdf':
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import mm
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from django.http import HttpResponse as HR

            buffer = _io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm)
            styles = getSampleStyleSheet()
            story = [Paragraph('Inventory Report', styles['Title']), Spacer(1, 5 * mm)]

            table_data = [['ID', 'Name', 'Category', 'Price', 'Cost', 'Qty', 'Reorder', 'Inv. Value']]
            for p in products:
                inv_value = float(p.price) * p.quantity
                table_data.append([
                    str(p.product_id),
                    p.product_name[:30],
                    p.category.name[:15] if p.category else '',
                    f'{float(p.price):.2f}',
                    f'{float(p.cost_price):.2f}' if p.cost_price else '-',
                    str(p.quantity),
                    str(p.reorder_level),
                    f'{inv_value:.2f}',
                ])

            t = Table(table_data, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(t)
            doc.build(story)
            buffer.seek(0)
            response = HR(buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="inventory.pdf"'
            return response

        return Response({'error': 'Unsupported format. Use ?format=csv or ?format=pdf'}, status=status.HTTP_400_BAD_REQUEST)


class ReorderSuggestionsView(APIView):
    """Products at or below reorder level, with last supplier delivery info."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        low_stock = Product.objects.select_related('category').filter(
            is_active=True,
            quantity__lte=F('reorder_level'),
        ).order_by('quantity')

        results = []
        for product in low_stock:
            last_delivery = product.supplier_deliveries.order_by('-delivery_date').first()
            results.append({
                'product_id': product.product_id,
                'product_name': product.product_name,
                'category': product.category.name if product.category else None,
                'current_quantity': product.quantity,
                'reorder_level': product.reorder_level,
                'units_below_reorder': product.reorder_level - product.quantity,
                'price': float(product.price),
                'cost_price': float(product.cost_price) if product.cost_price else None,
                'last_supplier': {
                    'supplier_name': last_delivery.supplier_name,
                    'unit_cost': float(last_delivery.unit_cost),
                    'delivery_date': str(last_delivery.delivery_date),
                    'quantity_received': last_delivery.quantity_received,
                } if last_delivery else None,
            })

        return Response(
            {'count': len(results), 'results': results},
            status=status.HTTP_200_OK
        )
