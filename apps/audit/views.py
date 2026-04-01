from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdmin
from apps.sales.models import Sale
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = AuditLog.objects.select_related('user').all()

        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)

        entity_type = request.query_params.get('entity_type')
        if entity_type:
            qs = qs.filter(entity_type=entity_type)

        action = request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)

        start_date = request.query_params.get('start_date')
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)

        end_date = request.query_params.get('end_date')
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        return Response(AuditLogSerializer(qs[:500], many=True).data)


class AuditLogDetailView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        try:
            log = AuditLog.objects.get(pk=pk)
        except AuditLog.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)
        return Response(AuditLogSerializer(log).data)


class AuditLogExportView(APIView):
    """Export audit log entries as a CSV file."""

    permission_classes = [IsAdmin]

    def get(self, request):
        import csv
        from django.http import HttpResponse

        qs = AuditLog.objects.select_related('user').all()

        start_date = request.query_params.get('start_date')
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)

        end_date = request.query_params.get('end_date')
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        action = request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_log.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'User', 'Action', 'Entity Type', 'Entity ID', 'Before Value', 'After Value', 'IP Address', 'Created At'])

        for log in qs.order_by('-created_at')[:5000]:
            writer.writerow([
                log.id,
                log.user.username if log.user else '',
                log.action,
                log.entity_type,
                log.entity_id,
                str(log.before_value) if log.before_value else '',
                str(log.after_value) if log.after_value else '',
                log.ip_address,
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])

        return response


class AnomalyReportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        anomalies = []

        # 1. Items voided >3x in one shift today
        from apps.sales.models import Sale
        void_count = Sale.objects.filter(status='voided', sale_date__date=today).count()
        if void_count > 3:
            anomalies.append({
                'type': 'high_voids',
                'message': f'{void_count} sales voided today (threshold: 3)',
                'severity': 'warning',
            })

        # 2. Products with price changes >2x this week
        price_changes = AuditLog.objects.filter(
            action='price_change',
            created_at__date__gte=week_ago,
        ).values('entity_id').annotate(change_count=Count('id')).filter(change_count__gte=2)
        for pc in price_changes:
            anomalies.append({
                'type': 'frequent_price_change',
                'message': f'Product #{pc["entity_id"]} changed price {pc["change_count"]} times this week',
                'severity': 'info',
            })

        # 3. Refunds > 10% of daily sales
        from django.db.models import Sum
        total_today = Sale.objects.filter(status='completed', sale_date__date=today).aggregate(t=Sum('total_amount'))['t'] or 0
        refund_today = Sale.objects.filter(status='refunded', sale_date__date=today).aggregate(t=Sum('total_amount'))['t'] or 0
        if total_today > 0 and refund_today > (float(total_today) * 0.1):
            anomalies.append({
                'type': 'high_refund_rate',
                'message': f'Refunds ({refund_today}) exceed 10% of daily sales ({total_today})',
                'severity': 'critical',
            })

        # 4. Multiple failed logins today
        failed_logins = AuditLog.objects.filter(
            action='login_failed',
            created_at__date=today,
        ).values('entity_id').annotate(count=Count('id')).filter(count__gte=3)
        for fl in failed_logins:
            anomalies.append({
                'type': 'multiple_failed_logins',
                'message': f'User #{fl["entity_id"]} had {fl["count"]} failed login attempts today',
                'severity': 'warning',
            })

        return Response({
            'date': str(today),
            'anomaly_count': len(anomalies),
            'anomalies': anomalies,
        })
