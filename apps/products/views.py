import base64
import io
import os

import qrcode
from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.authentication.permissions import IsAdminOrManager
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer, ProductListSerializer


class CategoryViewSet(ModelViewSet):
    """ViewSet for product categories."""

    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminOrManager()]

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        active_products = category.products.filter(is_active=True).count()
        if active_products > 0:
            return Response(
                {
                    'error': f'Cannot delete category. It has {active_products} active product(s). '
                             f'Please reassign or deactivate those products first.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductViewSet(ModelViewSet):
    """ViewSet for products."""

    queryset = Product.objects.select_related('category').filter(is_active=True)
    serializer_class = ProductSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminOrManager()]

    def get_queryset(self):
        from django.db.models import F
        queryset = Product.objects.select_related('category').all()

        # Filter out inactive products unless admin/manager
        show_inactive = self.request.query_params.get('show_inactive', 'false').lower() == 'true'
        if not show_inactive or self.request.user.role not in ['admin', 'manager']:
            queryset = queryset.filter(is_active=True)

        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Search by name or barcode
        search = self.request.query_params.get('search')
        if search:
            # If search looks like a barcode (digits only), try exact match first
            if search.isdigit():
                exact_match = queryset.filter(barcode=search)
                if exact_match.exists():
                    return exact_match.distinct()
            queryset = queryset.filter(
                product_name__icontains=search
            ) | queryset.filter(
                barcode__icontains=search
            )
            # Re-apply is_active filter after OR
            if not show_inactive or self.request.user.role not in ['admin', 'manager']:
                queryset = queryset.filter(is_active=True)

        # Low stock filter
        low_stock = self.request.query_params.get('low_stock', 'false').lower() == 'true'
        if low_stock:
            queryset = queryset.filter(quantity__lte=F('reorder_level'))

        # Sorting
        sort_param = self.request.query_params.get('sort', '')
        sort_map = {
            'price_asc': 'price',
            'price_desc': '-price',
            'name_asc': 'product_name',
            'name_desc': '-product_name',
            'quantity_asc': 'quantity',
            'quantity_desc': '-quantity',
        }
        order_by = sort_map.get(sort_param, 'product_name')
        return queryset.distinct().order_by(order_by)

    def update(self, request, *args, **kwargs):
        """Override update to log price changes to AuditLog."""
        product = self.get_object()
        old_price = str(product.price)
        old_cost_price = str(product.cost_price) if product.cost_price else None

        response = super().update(request, *args, **kwargs)

        product.refresh_from_db()
        new_price = str(product.price)
        new_cost_price = str(product.cost_price) if product.cost_price else None

        if old_price != new_price or old_cost_price != new_cost_price:
            try:
                from apps.audit.models import AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action='price_change',
                    entity_type='product',
                    entity_id=str(product.product_id),
                    before_value={'price': old_price, 'cost_price': old_cost_price},
                    after_value={'price': new_price, 'cost_price': new_cost_price},
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )
            except Exception:
                pass

        return response

    def partial_update(self, request, *args, **kwargs):
        """Delegate to update with partial=True, ensuring price logging."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Soft delete — set is_active=False instead of deleting."""
        product = self.get_object()
        product.is_active = False
        product.save(update_fields=['is_active'])
        return Response(
            {'message': f'Product "{product.product_name}" has been deactivated.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='reactivate')
    def reactivate(self, request, pk=None):
        """Reactivate a soft-deleted product."""
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        if product.is_active:
            return Response(
                {'message': 'Product is already active.'},
                status=status.HTTP_200_OK
            )

        product.is_active = True
        product.save(update_fields=['is_active'])
        return Response(
            {
                'message': f'Product "{product.product_name}" has been reactivated.',
                'product': ProductSerializer(product).data,
            },
            status=status.HTTP_200_OK
        )


class BarcodeLookupView(APIView):
    """Exact barcode lookup — returns the matching product or 404."""
    permission_classes = [IsAuthenticated]

    def get(self, request, barcode):
        try:
            product = Product.objects.select_related('category').get(barcode=barcode, is_active=True)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductSerializer(product).data)


class BarcodeGenerateView(APIView):
    """Generate and return a barcode PNG for a product."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            import barcode
            from barcode.writer import ImageWriter

            barcode_value = product.barcode or str(product.product_id).zfill(12)
            # Use Code128 which accepts any string
            Code128 = barcode.get_barcode_class('code128')
            buffer = io.BytesIO()
            Code128(barcode_value, writer=ImageWriter()).write(buffer)
            buffer.seek(0)

            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'barcodes'), exist_ok=True)
            return FileResponse(buffer, content_type='image/png', filename=f'barcode_{product.product_id}.png')
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QRCodeGenerateView(APIView):
    """Generate and return a QR code PNG for a product."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        import json as _json
        qr_data = _json.dumps({
            'product_id': product.product_id,
            'name': product.product_name,
            'price': str(product.price),
            'barcode': product.barcode or '',
        })
        img = qrcode.make(qr_data)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return FileResponse(buffer, content_type='image/png', filename=f'qr_{product.product_id}.png')


class BulkBarcodePDFView(APIView):
    """Generate a PDF with barcode labels for multiple products."""
    permission_classes = [IsAdminOrManager]

    def post(self, request):
        product_ids = request.data.get('product_ids', [])
        if not product_ids:
            return Response({'error': 'product_ids is required.'}, status=status.HTTP_400_BAD_REQUEST)

        products = Product.objects.filter(product_id__in=product_ids, is_active=True)
        if not products.exists():
            return Response({'error': 'No matching products found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas as rl_canvas

            buffer = io.BytesIO()
            c = rl_canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            x, y = 20 * mm, height - 30 * mm
            col_width = 70 * mm

            for i, product in enumerate(products):
                c.setFont('Helvetica', 10)
                c.drawString(x, y, product.product_name[:30])
                c.setFont('Helvetica', 8)
                c.drawString(x, y - 5 * mm, f'Price: GHS {product.price}')
                barcode_val = product.barcode or str(product.product_id).zfill(12)
                c.drawString(x, y - 10 * mm, f'Code: {barcode_val}')
                c.rect(x - 2 * mm, y - 14 * mm, col_width, 20 * mm)

                if (i + 1) % 3 == 0:
                    x = 20 * mm
                    y -= 30 * mm
                else:
                    x += col_width + 5 * mm

                if y < 30 * mm:
                    c.showPage()
                    x, y = 20 * mm, height - 30 * mm

            c.save()
            buffer.seek(0)
            return FileResponse(buffer, content_type='application/pdf', filename='barcodes.pdf')
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductBulkImportView(APIView):
    """Accept a CSV file upload and create products in bulk."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def post(self, request):
        import csv
        import io as _io
        from decimal import Decimal, InvalidOperation

        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'error': 'No file uploaded. Send a CSV file in the "file" field.'}, status=status.HTTP_400_BAD_REQUEST)

        if not csv_file.name.endswith('.csv'):
            return Response({'error': 'Only CSV files are supported.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(_io.StringIO(decoded))
        except Exception as exc:
            return Response({'error': f'Failed to parse CSV: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

        required_columns = {'name', 'price'}
        if reader.fieldnames:
            headers = {h.strip().lower() for h in reader.fieldnames}
        else:
            headers = set()

        if not required_columns.issubset(headers):
            return Response(
                {'error': f'CSV must contain at least: {", ".join(required_columns)}. Found: {", ".join(headers)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_products = []
        errors = []

        for row_num, row in enumerate(reader, start=2):
            row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            name = row.get('name', '').strip()
            if not name:
                errors.append({'row': row_num, 'error': 'Product name is required.'})
                continue

            try:
                price = Decimal(row.get('price', '0'))
            except InvalidOperation:
                errors.append({'row': row_num, 'error': f'Invalid price: {row.get("price")}'})
                continue

            cost_price = None
            if row.get('cost_price'):
                try:
                    cost_price = Decimal(row['cost_price'])
                except InvalidOperation:
                    pass

            try:
                quantity = int(row.get('quantity', 0))
            except (ValueError, TypeError):
                quantity = 0

            try:
                reorder_level = int(row.get('reorder_level', 5))
            except (ValueError, TypeError):
                reorder_level = 5

            barcode = row.get('barcode') or None
            description = row.get('description', '')
            category_name = row.get('category_name', '').strip()

            category = None
            if category_name:
                category, _ = Category.objects.get_or_create(name=category_name)

            # Skip duplicate barcodes
            if barcode and Product.objects.filter(barcode=barcode).exists():
                errors.append({'row': row_num, 'error': f'Barcode "{barcode}" already exists. Skipped.'})
                continue

            product = Product.objects.create(
                product_name=name,
                category=category,
                price=price,
                cost_price=cost_price,
                quantity=quantity,
                reorder_level=reorder_level,
                barcode=barcode,
                is_active=True,
            )
            created_products.append(product.product_id)

        return Response(
            {
                'created_count': len(created_products),
                'error_count': len(errors),
                'created_product_ids': created_products,
                'errors': errors,
            },
            status=status.HTTP_201_CREATED
        )
