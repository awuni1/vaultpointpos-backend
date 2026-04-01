from django.db.models import Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from apps.sales.models import Sale
from .models import SalesTarget, Achievement, CashierAchievement
from .serializers import SalesTargetSerializer, AchievementSerializer, CashierAchievementSerializer


class SalesTargetViewSet(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        targets = SalesTarget.objects.select_related('cashier', 'branch').all()
        cashier_id = request.query_params.get('cashier_id')
        if cashier_id:
            targets = targets.filter(cashier_id=cashier_id)
        return Response(SalesTargetSerializer(targets, many=True).data)

    def post(self, request):
        serializer = SalesTargetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TargetProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        user = request.user

        if user.role in ['admin', 'manager']:
            targets = SalesTarget.objects.filter(start_date__lte=today, end_date__gte=today)
        else:
            targets = SalesTarget.objects.filter(cashier=user, start_date__lte=today, end_date__gte=today)

        result = []
        for target in targets:
            sales_qs = Sale.objects.filter(
                status='completed',
                sale_date__date__gte=target.start_date,
                sale_date__date__lte=min(target.end_date, today),
            )
            if target.cashier:
                sales_qs = sales_qs.filter(user=target.cashier)

            achieved = sales_qs.aggregate(t=Sum('total_amount'))['t'] or 0
            pct = round(float(achieved) / float(target.target_amount) * 100, 1) if target.target_amount else 0

            result.append({
                'target': SalesTargetSerializer(target).data,
                'achieved': str(achieved),
                'percentage': min(pct, 100),
                'on_track': pct >= 50,
            })

        return Response(result)


class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', 'weekly')
        today = timezone.now().date()

        if period == 'daily':
            from_date = today
        elif period == 'monthly':
            from_date = today.replace(day=1)
        else:  # weekly
            from_date = today - timezone.timedelta(days=today.weekday())

        leaderboard = (
            Sale.objects.filter(status='completed', sale_date__date__gte=from_date)
            .values('user__user_id', 'user__full_name', 'user__username')
            .annotate(total_sales=Sum('total_amount'), transaction_count=Count('sale_id'))
            .order_by('-total_sales')[:10]
        )

        return Response({
            'period': period,
            'from_date': str(from_date),
            'leaderboard': [
                {
                    'rank': i + 1,
                    'cashier_id': str(row['user__user_id']),
                    'cashier_name': row['user__full_name'],
                    'username': row['user__username'],
                    'total_sales': str(row['total_sales']),
                    'transaction_count': row['transaction_count'],
                }
                for i, row in enumerate(leaderboard)
            ],
        })


class AchievementListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AchievementSerializer(Achievement.objects.all(), many=True).data)

    def post(self, request):
        if request.user.role not in ['admin', 'manager']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = AchievementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CashierAchievementsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.query_params.get('cashier_id')
        if user_id and request.user.role in ['admin', 'manager']:
            achievements = CashierAchievement.objects.filter(cashier_id=user_id)
        else:
            achievements = CashierAchievement.objects.filter(cashier=request.user)
        return Response(CashierAchievementSerializer(achievements, many=True).data)
