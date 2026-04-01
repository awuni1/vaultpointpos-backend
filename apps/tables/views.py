from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from .models import FloorPlan, Table, TableOrder, KitchenTicket
from .serializers import FloorPlanSerializer, TableSerializer, TableOrderSerializer, KitchenTicketSerializer


class TableListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tables = Table.objects.select_related('floor_plan').all()
        return Response(TableSerializer(tables, many=True).data)

    def post(self, request):
        if request.user.role not in ['admin', 'manager']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TableSerializer(data=request.data)
        if serializer.is_valid():
            table = serializer.save()
            pm_var_response = serializer.data
            return Response(pm_var_response, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FloorPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id):
        plans = FloorPlan.objects.filter(branch_id=branch_id).prefetch_related('tables')
        return Response(FloorPlanSerializer(plans, many=True).data)

    def post(self, request, branch_id):
        if request.user.role not in ['admin', 'manager']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        data = {**request.data, 'branch': branch_id}
        serializer = FloorPlanSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TableStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            table = Table.objects.get(pk=pk)
        except Table.DoesNotExist:
            return Response({'error': 'Table not found.'}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get('status')
        if new_status not in dict(Table.STATUS_CHOICES):
            return Response({'error': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
        table.status = new_status
        table.save(update_fields=['status'])
        return Response(TableSerializer(table).data)


class TableOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, table_id):
        try:
            table = Table.objects.get(pk=table_id)
        except Table.DoesNotExist:
            return Response({'error': 'Table not found.'}, status=status.HTTP_404_NOT_FOUND)

        if table.status == 'occupied':
            return Response({'error': 'Table is already occupied.'}, status=status.HTTP_400_BAD_REQUEST)

        order = TableOrder.objects.create(
            table=table,
            waiter=request.user,
            covers=request.data.get('covers', 1),
            notes=request.data.get('notes', ''),
        )
        table.status = 'occupied'
        table.save(update_fields=['status'])

        # Create kitchen ticket if items provided
        items = request.data.get('items', [])
        if items:
            KitchenTicket.objects.create(table_order=order, items=items)

        return Response(TableOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class TableOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return TableOrder.objects.select_related('table', 'waiter').prefetch_related('kitchen_tickets').get(pk=pk)
        except TableOrder.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(TableOrderSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TableOrderSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KitchenDisplayView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tickets = KitchenTicket.objects.filter(
            status__in=['pending', 'preparing']
        ).select_related('table_order__table').order_by('created_at')
        return Response(KitchenTicketSerializer(tickets, many=True).data)


class KitchenTicketUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            ticket = KitchenTicket.objects.get(pk=pk)
        except KitchenTicket.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        if new_status not in ('pending', 'preparing', 'ready'):
            return Response({'error': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)

        ticket.status = new_status
        if new_status == 'ready':
            ticket.ready_at = timezone.now()
            ticket.table_order.status = 'ready'
            ticket.table_order.save(update_fields=['status'])
        ticket.save()
        return Response(KitchenTicketSerializer(ticket).data)


class SplitBillView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = TableOrder.objects.get(pk=pk)
        except TableOrder.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not order.sale:
            return Response({'error': 'No sale linked to this order yet.'}, status=status.HTTP_400_BAD_REQUEST)

        split_by = int(request.data.get('split_by', 2))
        if split_by < 2:
            return Response({'error': 'split_by must be at least 2.'}, status=status.HTTP_400_BAD_REQUEST)

        per_person = order.sale.total_amount / split_by
        return Response({
            'total': str(order.sale.total_amount),
            'split_by': split_by,
            'per_person': str(round(per_person, 2)),
        })
