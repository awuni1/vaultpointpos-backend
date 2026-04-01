from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from apps.sales.models import Sale
from .models import Shift
from .serializers import ShiftSerializer, ShiftStartSerializer, ShiftEndSerializer


class ShiftStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if cashier already has an open shift
        open_shift = Shift.objects.filter(cashier=request.user, status='open').first()
        if open_shift:
            return Response(
                {'error': 'You already have an open shift.', 'shift_id': open_shift.id},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ShiftStartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        branch = None
        if data.get('branch_id'):
            from apps.branches.models import Branch
            try:
                branch = Branch.objects.get(pk=data['branch_id'])
            except Branch.DoesNotExist:
                return Response({'error': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)

        shift = Shift.objects.create(
            cashier=request.user,
            branch=branch,
            opening_float=data['opening_float'],
            notes=data.get('notes', ''),
        )
        return Response(ShiftSerializer(shift).data, status=status.HTTP_201_CREATED)


class ShiftEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            shift = Shift.objects.get(pk=pk)
        except Shift.DoesNotExist:
            return Response({'error': 'Shift not found.'}, status=status.HTTP_404_NOT_FOUND)

        if shift.cashier != request.user and request.user.role not in ['admin', 'manager']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        if shift.status == 'closed':
            return Response({'error': 'Shift is already closed.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ShiftEndSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        shift.ended_at = timezone.now()
        shift.closing_cash = serializer.validated_data['closing_cash']
        shift.expected_cash = shift.calculate_expected_cash()
        shift.variance = shift.closing_cash - shift.expected_cash
        shift.status = 'closed'
        if serializer.validated_data.get('notes'):
            shift.notes = serializer.validated_data['notes']
        shift.save()
        return Response(ShiftSerializer(shift).data)


class ShiftListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role in ['admin', 'manager']:
            shifts = Shift.objects.select_related('cashier', 'branch').all()
        else:
            shifts = Shift.objects.filter(cashier=request.user)

        cashier_id = request.query_params.get('cashier_id')
        if cashier_id and request.user.role in ['admin', 'manager']:
            shifts = shifts.filter(cashier_id=cashier_id)

        status_filter = request.query_params.get('status')
        if status_filter:
            shifts = shifts.filter(status=status_filter)

        return Response(ShiftSerializer(shifts, many=True).data)


class ShiftDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            shift = Shift.objects.select_related('cashier', 'branch').get(pk=pk)
        except Shift.DoesNotExist:
            return Response({'error': 'Shift not found.'}, status=status.HTTP_404_NOT_FOUND)

        if shift.cashier != request.user and request.user.role not in ['admin', 'manager']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        return Response(ShiftSerializer(shift).data)


class ShiftReconciliationView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request, pk):
        try:
            shift = Shift.objects.select_related('cashier').get(pk=pk)
        except Shift.DoesNotExist:
            return Response({'error': 'Shift not found.'}, status=status.HTTP_404_NOT_FOUND)

        from django.db.models import Sum, Count
        sales_qs = Sale.objects.filter(user=shift.cashier, sale_date__gte=shift.started_at)
        if shift.ended_at:
            sales_qs = sales_qs.filter(sale_date__lte=shift.ended_at)

        completed = sales_qs.filter(status='completed')
        by_method = {}
        for method in ['cash', 'mobile_money', 'card', 'split']:
            agg = completed.filter(payment_method=method).aggregate(
                total=Sum('total_amount'), count=Count('sale_id')
            )
            by_method[method] = {'total': str(agg['total'] or 0), 'count': agg['count']}

        return Response({
            'shift': ShiftSerializer(shift).data,
            'sales_by_payment_method': by_method,
            'total_sales': str(completed.aggregate(t=Sum('total_amount'))['t'] or 0),
            'transaction_count': completed.count(),
            'void_count': sales_qs.filter(status='voided').count(),
            'refund_count': sales_qs.filter(status='refunded').count(),
            'opening_float': str(shift.opening_float),
            'closing_cash': str(shift.closing_cash) if shift.closing_cash is not None else None,
            'expected_cash': str(shift.expected_cash) if shift.expected_cash is not None else None,
            'variance': str(shift.variance) if shift.variance is not None else None,
            'variance_flag': abs(shift.variance) > 5 if shift.variance is not None else False,
        })
