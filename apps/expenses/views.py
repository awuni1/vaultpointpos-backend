from django.db.models import Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from apps.sales.models import Sale
from .models import Expense, ExpenseCategory
from .serializers import ExpenseSerializer, ExpenseCategorySerializer


class ExpenseCategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ExpenseCategorySerializer(ExpenseCategory.objects.all(), many=True).data)

    def post(self, request):
        if request.user.role not in ['admin', 'manager']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = ExpenseCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExpenseCategoryDetailView(APIView):
    permission_classes = [IsAdminOrManager]

    def get_object(self, pk):
        try:
            return ExpenseCategory.objects.get(pk=pk)
        except ExpenseCategory.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ExpenseCategorySerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ExpenseCategorySerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExpenseListView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        qs = Expense.objects.select_related('category', 'recorded_by').all()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        category = request.query_params.get('category')
        if category:
            qs = qs.filter(category_id=category)
        return Response(ExpenseSerializer(qs, many=True).data)

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(recorded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExpenseDetailView(APIView):
    permission_classes = [IsAdminOrManager]

    def get_object(self, pk):
        try:
            return Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ExpenseSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ExpenseSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExpenseSummaryView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        qs = Expense.objects.filter(status='approved')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        by_category = (
            qs.values('category__name')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )
        total = qs.aggregate(t=Sum('amount'))['t'] or 0
        return Response({
            'total_expenses': str(total),
            'by_category': [
                {'category': r['category__name'] or 'Uncategorised', 'total': str(r['total'])}
                for r in by_category
            ],
        })


class ProfitReportView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        sales_qs = Sale.objects.filter(status='completed')
        expense_qs = Expense.objects.filter(status='approved')

        if start_date:
            sales_qs = sales_qs.filter(sale_date__date__gte=start_date)
            expense_qs = expense_qs.filter(date__gte=start_date)
        if end_date:
            sales_qs = sales_qs.filter(sale_date__date__lte=end_date)
            expense_qs = expense_qs.filter(date__lte=end_date)

        revenue = sales_qs.aggregate(t=Sum('total_amount'))['t'] or 0
        expenses = expense_qs.aggregate(t=Sum('amount'))['t'] or 0
        net_profit = revenue - expenses

        return Response({
            'period': {'start_date': start_date, 'end_date': end_date},
            'revenue': str(revenue),
            'expenses': str(expenses),
            'net_profit': str(net_profit),
        })
