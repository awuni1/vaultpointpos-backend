import os
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sales.models import Sale
from .models import Receipt
from .serializers import ReceiptSerializer, ReceiptItemSerializer


def _get_business_info():
    """Retrieve business info from SystemSettings, with fallback defaults."""
    try:
        from apps.authentication.models import SystemSettings
        settings_obj = SystemSettings.get_settings()
        return {
            'name': settings_obj.store_name or 'SwiftPOS Store',
            'address': settings_obj.store_address or '123 Main Street, City',
            'phone': settings_obj.store_phone or '+1 (555) 000-0000',
            'footer': settings_obj.receipt_footer or 'Thank you for your purchase!',
        }
    except Exception:
        return {
            'name': 'SwiftPOS Store',
            'address': '123 Main Street, City',
            'phone': '+1 (555) 000-0000',
            'footer': 'Thank you for your purchase!',
        }


def build_receipt_data(sale):
    """Build the receipt data dictionary from a sale object."""
    receipt = getattr(sale, 'receipt', None)
    biz = _get_business_info()

    items_data = []
    for item in sale.items.all():
        items_data.append({
            'product': item.product,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'discount_pct': item.discount_pct,
            'line_total': item.line_total,
        })

    customer = sale.customer
    loyalty_points_earned = int(sale.total_amount) if customer else 0

    return {
        'receipt_id': receipt.receipt_id if receipt else None,
        'sale_id': sale.sale_id,
        'sale_date': sale.sale_date,
        'generated_at': receipt.generated_at if receipt else timezone.now(),
        'cashier_name': sale.user.full_name if sale.user else 'Unknown',
        'cashier_username': sale.user.username if sale.user else 'unknown',
        'customer_id': customer.customer_id if customer else None,
        'customer_name': customer.full_name if customer else None,
        'customer_phone': customer.phone if customer else None,
        'loyalty_points_earned': loyalty_points_earned,
        'items': items_data,
        'subtotal': sale.subtotal,
        'discount_amount': sale.discount_amount,
        'tax_rate': sale.tax_rate,
        'tax_amount': sale.tax_amount,
        'total_amount': sale.total_amount,
        'payment_method': sale.get_payment_method_display(),
        'status': sale.get_status_display(),
        'business_name': biz['name'],
        'business_address': biz['address'],
        'business_phone': biz['phone'],
    }


class ReceiptDetailView(APIView):
    """Return formatted receipt data for a given sale."""

    permission_classes = [IsAuthenticated]

    def get(self, request, sale_id):
        try:
            sale = Sale.objects.select_related(
                'user', 'customer'
            ).prefetch_related('items__product').get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Cashiers can only view their own sale receipts
        if request.user.role == 'cashier' and sale.user != request.user:
            return Response(
                {'error': 'You do not have permission to view this receipt.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get or create receipt record
        receipt, created = Receipt.objects.get_or_create(sale=sale)

        receipt_data = build_receipt_data(sale)
        serializer = ReceiptSerializer(receipt_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReceiptPDFView(APIView):
    """Generate a PDF receipt for a given sale using ReportLab."""

    permission_classes = [IsAuthenticated]

    def get(self, request, sale_id):
        try:
            sale = Sale.objects.select_related(
                'user', 'customer'
            ).prefetch_related('items__product').get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Cashiers can only view their own sale receipts
        if request.user.role == 'cashier' and sale.user != request.user:
            return Response(
                {'error': 'You do not have permission to generate this receipt.'},
                status=status.HTTP_403_FORBIDDEN
            )

        receipt_data = build_receipt_data(sale)
        pdf_buffer = self._generate_pdf(receipt_data)

        # Save PDF path
        receipt, _ = Receipt.objects.get_or_create(sale=sale)
        pdf_filename = f'receipt_sale_{sale_id}.pdf'
        pdf_dir = os.path.join(settings.MEDIA_ROOT, 'receipts')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        with open(pdf_path, 'wb') as f:
            f.write(pdf_buffer.getvalue())

        receipt.pdf_path = f'receipts/{pdf_filename}'
        receipt.save(update_fields=['pdf_path'])

        pdf_buffer.seek(0)
        response = FileResponse(
            pdf_buffer,
            content_type='application/pdf',
        )
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response

    def _generate_pdf(self, data):
        """Generate PDF using ReportLab and return as BytesIO buffer."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.platypus import KeepTogether

        buffer = BytesIO()
        # Use 80mm wide receipt paper format
        page_width = 80 * mm
        page_height = A4[1]

        doc = SimpleDocTemplate(
            buffer,
            pagesize=(page_width, page_height),
            rightMargin=5 * mm,
            leftMargin=5 * mm,
            topMargin=5 * mm,
            bottomMargin=5 * mm,
        )

        styles = getSampleStyleSheet()
        center_style = ParagraphStyle('center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)
        bold_center = ParagraphStyle('bold_center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, fontName='Helvetica-Bold')
        right_style = ParagraphStyle('right', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=8)
        left_style = ParagraphStyle('left', parent=styles['Normal'], alignment=TA_LEFT, fontSize=8)
        title_style = ParagraphStyle('title', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, fontName='Helvetica-Bold')

        story = []

        # Business header
        story.append(Paragraph(data['business_name'], title_style))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(data['business_address'], center_style))
        story.append(Paragraph(data['business_phone'], center_style))
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black))
        story.append(Spacer(1, 2 * mm))

        # Sale details
        sale_date_str = data['sale_date'].strftime('%Y-%m-%d %H:%M:%S')
        story.append(Paragraph(f'<b>Receipt #:</b> {data["sale_id"]}', left_style))
        story.append(Paragraph(f'<b>Date:</b> {sale_date_str}', left_style))
        story.append(Paragraph(f'<b>Cashier:</b> {data["cashier_name"]}', left_style))
        if data['customer_name']:
            story.append(Paragraph(f'<b>Customer:</b> {data["customer_name"]}', left_style))
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black))
        story.append(Spacer(1, 2 * mm))

        # Items table
        table_data = [['Item', 'Qty', 'Price', 'Total']]
        for item in data['items']:
            product_name = item['product'].product_name if item['product'] else 'Unknown'
            # Truncate long names
            if len(product_name) > 18:
                product_name = product_name[:15] + '...'
            table_data.append([
                product_name,
                str(item['quantity']),
                f'{item["unit_price"]:.2f}',
                f'{item["line_total"]:.2f}',
            ])

        item_table = Table(
            table_data,
            colWidths=[30 * mm, 10 * mm, 14 * mm, 14 * mm],
        )
        item_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        story.append(item_table)

        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black))
        story.append(Spacer(1, 2 * mm))

        # Totals
        story.append(Paragraph(f'Subtotal: {data["subtotal"]:.2f}', right_style))
        if data['discount_amount'] and data['discount_amount'] > 0:
            story.append(Paragraph(f'Discount: -{data["discount_amount"]:.2f}', right_style))
        if data['tax_amount'] and data['tax_amount'] > 0:
            story.append(Paragraph(f'Tax ({data["tax_rate"]}%): {data["tax_amount"]:.2f}', right_style))

        story.append(HRFlowable(width='100%', thickness=1, color=colors.black))
        story.append(Paragraph(f'<b>TOTAL: {data["total_amount"]:.2f}</b>', right_style))
        story.append(Spacer(1, 2 * mm))

        # Payment info
        story.append(Paragraph(f'Payment: {data["payment_method"]}', left_style))
        if data.get('loyalty_points_earned'):
            story.append(Paragraph(f'Loyalty points earned: {data["loyalty_points_earned"]}', left_style))

        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black))
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph('Thank you for your purchase!', center_style))
        story.append(Paragraph('Please come again.', center_style))

        doc.build(story)
        buffer.seek(0)
        return buffer
