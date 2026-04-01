import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate, TruncHour, ExtractHour
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from apps.products.models import Product
from apps.sales.models import Sale, SaleItem
from apps.payments.models import Payment
from .serializers import (
    CashierPerformanceSerializer,
    DailySalesSerializer,
    InventoryReportSerializer,
    MonthlySalesSerializer,
    PaymentMethodReportSerializer,
    ProductPerformanceSerializer,
    WeeklySalesSerializer,
)


def get_payment_breakdown(sales_qs):
    """Get payment method breakdown for a queryset of sales."""
    breakdown = {}
    for method, label in Sale.PAYMENT_METHOD_CHOICES:
        method_sales = sales_qs.filter(payment_method=method)
        agg = method_sales.aggregate(count=Count('sale_id'), total=Sum('total_amount'))
        breakdown[method] = {
            'label': label,
            'count': agg['count'] or 0,
            'total': float(agg['total'] or 0),
        }
    return breakdown


class DailySalesReportView(APIView):
    """Daily sales summary report."""

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
            report_date = date.today()

        all_sales = Sale.objects.filter(sale_date__date=report_date)
        completed = all_sales.filter(status='completed')

        totals = completed.aggregate(
            total_revenue=Sum('total_amount'),
            total_discount=Sum('discount_amount'),
            total_tax=Sum('tax_amount'),
        )

        # Top products for the day
        top_items = SaleItem.objects.filter(
            sale__sale_date__date=report_date,
            sale__status='completed',
        ).values(
            'product__product_id',
            'product__product_name',
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('line_total'),
        ).order_by('-total_revenue')[:10]

        top_products = [
            {
                'product_id': item['product__product_id'],
                'product_name': item['product__product_name'],
                'quantity_sold': item['total_quantity'],
                'revenue': float(item['total_revenue'] or 0),
            }
            for item in top_items
        ]

        # Hourly breakdown
        hourly = completed.annotate(
            hour=ExtractHour('sale_date')
        ).values('hour').annotate(
            sales_count=Count('sale_id'),
            revenue=Sum('total_amount'),
        ).order_by('hour')

        hourly_breakdown = [
            {
                'hour': f'{item["hour"]:02d}:00',
                'sales_count': item['sales_count'],
                'revenue': float(item['revenue'] or 0),
            }
            for item in hourly
        ]

        total_revenue = totals.get('total_revenue') or Decimal('0.00')
        total_discount = totals.get('total_discount') or Decimal('0.00')
        total_tax = totals.get('total_tax') or Decimal('0.00')
        net_revenue = total_revenue - total_discount

        data = {
            'date': report_date,
            'total_sales': all_sales.count(),
            'total_revenue': total_revenue,
            'total_discount': total_discount,
            'total_tax': total_tax,
            'net_revenue': net_revenue,
            'completed_sales': completed.count(),
            'voided_sales': all_sales.filter(status='voided').count(),
            'refunded_sales': all_sales.filter(status='refunded').count(),
            'payment_breakdown': get_payment_breakdown(completed),
            'top_products': top_products,
            'hourly_breakdown': hourly_breakdown,
        }

        serializer = DailySalesSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WeeklySalesReportView(APIView):
    """Weekly sales report starting from a given date."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        start_date_str = request.query_params.get('start_date')
        if start_date_str:
            start_date = parse_date(start_date_str)
            if not start_date:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            today = date.today()
            start_date = today - timedelta(days=today.weekday())

        end_date = start_date + timedelta(days=6)

        completed_sales = Sale.objects.filter(
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date,
            status='completed',
        )

        totals = completed_sales.aggregate(
            total_revenue=Sum('total_amount'),
        )
        total_revenue = totals.get('total_revenue') or Decimal('0.00')
        total_count = completed_sales.count()
        days_in_range = (end_date - start_date).days + 1
        avg_daily = total_revenue / days_in_range if days_in_range > 0 else Decimal('0.00')

        # Daily breakdown
        daily_data = completed_sales.annotate(
            day=TruncDate('sale_date')
        ).values('day').annotate(
            count=Count('sale_id'),
            revenue=Sum('total_amount'),
        ).order_by('day')

        daily_breakdown = [
            {
                'date': item['day'].isoformat() if item['day'] else None,
                'sales_count': item['count'],
                'revenue': float(item['revenue'] or 0),
            }
            for item in daily_data
        ]

        data = {
            'start_date': start_date,
            'end_date': end_date,
            'total_sales': total_count,
            'total_revenue': total_revenue,
            'average_daily_revenue': avg_daily,
            'daily_breakdown': daily_breakdown,
            'payment_breakdown': get_payment_breakdown(completed_sales),
        }

        serializer = WeeklySalesSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MonthlySalesReportView(APIView):
    """Monthly sales report for a given year and month."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        today = date.today()
        try:
            year = int(request.query_params.get('year', today.year))
            month = int(request.query_params.get('month', today.month))
        except ValueError:
            return Response(
                {'error': 'Invalid year or month. Both must be integers.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not (1 <= month <= 12):
            return Response(
                {'error': 'Month must be between 1 and 12.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        _, days_in_month = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, days_in_month)

        all_sales = Sale.objects.filter(
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date,
        )
        completed_sales = all_sales.filter(status='completed')

        totals = completed_sales.aggregate(
            total_revenue=Sum('total_amount'),
            total_discount=Sum('discount_amount'),
            total_tax=Sum('tax_amount'),
            avg_transaction=Avg('total_amount'),
        )

        total_revenue = totals.get('total_revenue') or Decimal('0.00')
        total_discount = totals.get('total_discount') or Decimal('0.00')
        total_tax = totals.get('total_tax') or Decimal('0.00')
        net_revenue = total_revenue - total_discount
        avg_transaction = totals.get('avg_transaction') or Decimal('0.00')

        # Daily breakdown
        daily_data = completed_sales.annotate(
            day=TruncDate('sale_date')
        ).values('day').annotate(
            count=Count('sale_id'),
            revenue=Sum('total_amount'),
        ).order_by('day')

        daily_breakdown = [
            {
                'date': item['day'].isoformat() if item['day'] else None,
                'sales_count': item['count'],
                'revenue': float(item['revenue'] or 0),
            }
            for item in daily_data
        ]

        data = {
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'total_sales': completed_sales.count(),
            'total_revenue': total_revenue,
            'total_discount': total_discount,
            'total_tax': total_tax,
            'net_revenue': net_revenue,
            'average_transaction_value': avg_transaction,
            'daily_breakdown': daily_breakdown,
            'payment_breakdown': get_payment_breakdown(completed_sales),
        }

        serializer = MonthlySalesSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductPerformanceView(APIView):
    """Product performance report over a date range."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        today = date.today()
        start_date = parse_date(start_date_str) if start_date_str else today - timedelta(days=30)
        end_date = parse_date(end_date_str) if end_date_str else today

        if not start_date or not end_date:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        products = SaleItem.objects.filter(
            sale__sale_date__date__gte=start_date,
            sale__sale_date__date__lte=end_date,
            sale__status='completed',
        ).values(
            'product__product_id',
            'product__product_name',
            'product__category__name',
            'product__price',
            'product__cost_price',
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('line_total'),
            transaction_count=Count('sale', distinct=True),
        ).order_by('-total_revenue')

        product_list = []
        total_revenue = Decimal('0.00')

        for item in products:
            revenue = item.get('total_revenue') or Decimal('0.00')
            total_revenue += revenue
            cost_price = item.get('product__cost_price') or Decimal('0.00')
            quantity = item.get('total_quantity') or 0
            gross_profit = revenue - (cost_price * quantity) if cost_price else None

            product_list.append({
                'product_id': item['product__product_id'],
                'product_name': item['product__product_name'],
                'category': item['product__category__name'],
                'current_price': float(item['product__price'] or 0),
                'total_quantity_sold': quantity,
                'total_revenue': float(revenue),
                'transaction_count': item['transaction_count'],
                'gross_profit': float(gross_profit) if gross_profit is not None else None,
            })

        data = {
            'start_date': start_date,
            'end_date': end_date,
            'products': product_list,
            'total_revenue': total_revenue,
        }

        serializer = ProductPerformanceSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InventoryReportView(APIView):
    """Current inventory valuation and stock report."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        all_products = Product.objects.select_related('category').all()
        active_products = all_products.filter(is_active=True)

        # Stock calculations
        low_stock = active_products.filter(quantity__lte=F('reorder_level'))
        out_of_stock = active_products.filter(quantity=0)

        # Inventory value (price * quantity)
        total_inventory_value = sum(
            (p.price * p.quantity) for p in active_products
        )
        total_cost_value = sum(
            (p.cost_price * p.quantity) for p in active_products if p.cost_price
        )

        # By category
        from apps.products.models import Category
        categories = Category.objects.all()
        cat_list = []
        for cat in categories:
            cat_products = active_products.filter(category=cat)
            cat_value = sum((p.price * p.quantity) for p in cat_products)
            cat_list.append({
                'category_id': cat.category_id,
                'category_name': cat.name,
                'product_count': cat_products.count(),
                'inventory_value': float(cat_value),
            })

        # Low stock list
        low_stock_list = [
            {
                'product_id': p.product_id,
                'product_name': p.product_name,
                'current_quantity': p.quantity,
                'reorder_level': p.reorder_level,
                'units_below_reorder': p.reorder_level - p.quantity,
            }
            for p in low_stock.order_by('quantity')
        ]

        data = {
            'generated_at': timezone.now(),
            'total_products': all_products.count(),
            'active_products': active_products.count(),
            'low_stock_count': low_stock.count(),
            'out_of_stock_count': out_of_stock.count(),
            'total_inventory_value': total_inventory_value,
            'total_cost_value': total_cost_value,
            'categories': cat_list,
            'low_stock_products': low_stock_list,
        }

        serializer = InventoryReportSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CashierPerformanceView(APIView):
    """Cashier performance report over a date range."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        today = date.today()
        start_date = parse_date(start_date_str) if start_date_str else today - timedelta(days=30)
        end_date = parse_date(end_date_str) if end_date_str else today

        if not start_date or not end_date:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cashier_data = Sale.objects.filter(
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date,
            status='completed',
        ).values(
            'user__user_id',
            'user__username',
            'user__full_name',
            'user__role',
        ).annotate(
            total_sales=Count('sale_id'),
            total_revenue=Sum('total_amount'),
            avg_transaction=Avg('total_amount'),
        ).order_by('-total_revenue')

        cashiers = [
            {
                'user_id': str(item['user__user_id']),
                'username': item['user__username'],
                'full_name': item['user__full_name'],
                'role': item['user__role'],
                'total_sales': item['total_sales'],
                'total_revenue': float(item['total_revenue'] or 0),
                'average_transaction': float(item['avg_transaction'] or 0),
            }
            for item in cashier_data
        ]

        data = {
            'start_date': start_date,
            'end_date': end_date,
            'cashiers': cashiers,
        }

        serializer = CashierPerformanceSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentMethodReportView(APIView):
    """Payment method breakdown report."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        today = date.today()
        start_date = parse_date(start_date_str) if start_date_str else today - timedelta(days=30)
        end_date = parse_date(end_date_str) if end_date_str else today

        if not start_date or not end_date:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        completed_sales = Sale.objects.filter(
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date,
            status='completed',
        )

        totals = completed_sales.aggregate(
            total_revenue=Sum('total_amount'),
            total_transactions=Count('sale_id'),
        )

        total_revenue = totals.get('total_revenue') or Decimal('0.00')
        total_transactions = totals.get('total_transactions') or 0

        # Breakdown by payment method
        payment_methods = []
        for method, label in Sale.PAYMENT_METHOD_CHOICES:
            method_sales = completed_sales.filter(payment_method=method)
            agg = method_sales.aggregate(
                count=Count('sale_id'),
                total=Sum('total_amount'),
            )
            count = agg.get('count') or 0
            method_total = agg.get('total') or Decimal('0.00')
            percentage = (float(method_total) / float(total_revenue) * 100) if total_revenue > 0 else 0

            payment_methods.append({
                'method': method,
                'label': label,
                'transaction_count': count,
                'total_amount': float(method_total),
                'percentage': round(percentage, 2),
            })

        data = {
            'start_date': start_date,
            'end_date': end_date,
            'total_revenue': total_revenue,
            'total_transactions': total_transactions,
            'payment_methods': payment_methods,
        }

        serializer = PaymentMethodReportSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoryRevenueReportView(APIView):
    """Groups sales revenue by product category for a date range."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        today = date.today()
        start_date = parse_date(start_date_str) if start_date_str else today - timedelta(days=30)
        end_date = parse_date(end_date_str) if end_date_str else today

        if not start_date or not end_date:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        category_data = SaleItem.objects.filter(
            sale__sale_date__date__gte=start_date,
            sale__sale_date__date__lte=end_date,
            sale__status='completed',
        ).values(
            'product__category__category_id',
            'product__category__name',
        ).annotate(
            total_revenue=Sum('line_total'),
            total_quantity=Sum('quantity'),
            transaction_count=Count('sale', distinct=True),
        ).order_by('-total_revenue')

        grand_total = sum(float(item['total_revenue'] or 0) for item in category_data)

        categories = []
        for item in category_data:
            revenue = float(item['total_revenue'] or 0)
            categories.append({
                'category_id': item['product__category__category_id'],
                'category_name': item['product__category__name'] or 'Uncategorized',
                'total_revenue': revenue,
                'total_quantity_sold': item['total_quantity'] or 0,
                'transaction_count': item['transaction_count'] or 0,
                'percentage': round(revenue / grand_total * 100, 2) if grand_total > 0 else 0,
            })

        return Response({
            'start_date': str(start_date),
            'end_date': str(end_date),
            'total_revenue': grand_total,
            'categories': categories,
        }, status=status.HTTP_200_OK)


class CustomerReportView(APIView):
    """Customer report: totals, new customers, top spenders."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        from apps.customers.models import Customer
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        today = date.today()
        start_date = parse_date(start_date_str) if start_date_str else date(today.year, today.month, 1)
        end_date = parse_date(end_date_str) if end_date_str else today

        total_customers = Customer.objects.count()

        new_customers = Customer.objects.filter(
            registered_at__date__gte=start_date,
            registered_at__date__lte=end_date,
        ).count()

        top_customers_qs = Customer.objects.order_by('-total_spent')[:10]
        top_customers = [
            {
                'customer_id': c.customer_id,
                'full_name': c.full_name,
                'phone': c.phone,
                'email': c.email,
                'total_spent': float(c.total_spent),
                'loyalty_points': c.loyalty_points,
            }
            for c in top_customers_qs
        ]

        return Response({
            'start_date': str(start_date),
            'end_date': str(end_date),
            'total_customers': total_customers,
            'new_customers_in_period': new_customers,
            'top_customers': top_customers,
        }, status=status.HTTP_200_OK)


class ReportExportView(APIView):
    """Export various reports as CSV or PDF."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        import csv
        import io as _io
        from django.http import HttpResponse
        from django.utils.dateparse import parse_date as _parse_date

        report_type = request.query_params.get('report', 'daily')
        fmt = request.query_params.get('format', 'csv').lower()
        date_str = request.query_params.get('date')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        today = date.today()
        start_date = _parse_date(start_date_str) if start_date_str else today - timedelta(days=30)
        end_date = _parse_date(end_date_str) if end_date_str else today
        report_date = _parse_date(date_str) if date_str else today

        # Build the data rows depending on report type
        headers = []
        rows = []
        title = report_type.replace('_', ' ').title() + ' Report'

        if report_type == 'daily':
            sales = Sale.objects.filter(sale_date__date=report_date, status='completed')
            headers = ['Sale ID', 'Date', 'Cashier', 'Customer', 'Total', 'Payment Method']
            for s in sales:
                rows.append([
                    s.sale_id,
                    s.sale_date.strftime('%Y-%m-%d %H:%M'),
                    s.user.full_name if s.user else '',
                    s.customer.full_name if s.customer else '',
                    float(s.total_amount),
                    s.payment_method,
                ])
            title = f'Daily Sales Report — {report_date}'

        elif report_type in ('weekly', 'monthly'):
            sales = Sale.objects.filter(
                sale_date__date__gte=start_date,
                sale_date__date__lte=end_date,
                status='completed',
            )
            headers = ['Sale ID', 'Date', 'Cashier', 'Customer', 'Total', 'Payment Method']
            for s in sales:
                rows.append([
                    s.sale_id,
                    s.sale_date.strftime('%Y-%m-%d %H:%M'),
                    s.user.full_name if s.user else '',
                    s.customer.full_name if s.customer else '',
                    float(s.total_amount),
                    s.payment_method,
                ])
            title = f'{report_type.title()} Sales Report — {start_date} to {end_date}'

        elif report_type == 'products':
            items = SaleItem.objects.filter(
                sale__sale_date__date__gte=start_date,
                sale__sale_date__date__lte=end_date,
                sale__status='completed',
            ).values(
                'product__product_id', 'product__product_name', 'product__category__name',
            ).annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum('line_total'),
            ).order_by('-total_revenue')
            headers = ['Product ID', 'Name', 'Category', 'Qty Sold', 'Revenue']
            for item in items:
                rows.append([
                    item['product__product_id'],
                    item['product__product_name'],
                    item['product__category__name'] or '',
                    item['total_quantity'],
                    float(item['total_revenue'] or 0),
                ])

        elif report_type == 'inventory':
            products = Product.objects.select_related('category').filter(is_active=True)
            headers = ['ID', 'Name', 'Category', 'Price', 'Cost', 'Quantity', 'Reorder Level', 'Inv. Value']
            for p in products:
                rows.append([
                    p.product_id, p.product_name,
                    p.category.name if p.category else '',
                    float(p.price),
                    float(p.cost_price) if p.cost_price else '',
                    p.quantity, p.reorder_level,
                    round(float(p.price) * p.quantity, 2),
                ])

        elif report_type == 'cashiers':
            cashier_data = Sale.objects.filter(
                sale_date__date__gte=start_date,
                sale_date__date__lte=end_date,
                status='completed',
            ).values('user__username', 'user__full_name').annotate(
                total_sales=Count('sale_id'),
                total_revenue=Sum('total_amount'),
            ).order_by('-total_revenue')
            headers = ['Username', 'Full Name', 'Total Sales', 'Total Revenue']
            for item in cashier_data:
                rows.append([
                    item['user__username'], item['user__full_name'],
                    item['total_sales'], float(item['total_revenue'] or 0),
                ])

        elif report_type == 'payment_methods':
            headers = ['Method', 'Count', 'Total Amount']
            completed = Sale.objects.filter(
                sale_date__date__gte=start_date,
                sale_date__date__lte=end_date,
                status='completed',
            )
            for method, label in Sale.PAYMENT_METHOD_CHOICES:
                agg = completed.filter(payment_method=method).aggregate(
                    count=Count('sale_id'), total=Sum('total_amount')
                )
                rows.append([label, agg['count'] or 0, float(agg['total'] or 0)])

        else:
            return Response({'error': f'Unknown report type: {report_type}'}, status=status.HTTP_400_BAD_REQUEST)

        if fmt == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            return response

        elif fmt == 'pdf':
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import mm
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet

            buffer = _io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm)
            styles = getSampleStyleSheet()
            story = [Paragraph(title, styles['Title']), Spacer(1, 5 * mm)]

            table_data = [headers] + [[str(cell) for cell in row] for row in rows]
            if len(table_data) > 1:
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
            else:
                story.append(Paragraph('No data available.', styles['Normal']))

            doc.build(story)
            buffer.seek(0)
            response = HttpResponse(buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
            return response

        return Response({'error': 'Unsupported format. Use ?format=csv or ?format=pdf'}, status=status.HTTP_400_BAD_REQUEST)
