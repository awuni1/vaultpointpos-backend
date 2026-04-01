from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from apps.inventory.models import StockMovement
from .models import Supplier, PurchaseOrder, SupplierPerformance
from .serializers import (
    SupplierSerializer, PurchaseOrderSerializer,
    PurchaseOrderCreateSerializer, SupplierPerformanceSerializer,
)


class SupplierListView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        suppliers = Supplier.objects.filter(is_active=True)
        return Response(SupplierSerializer(suppliers, many=True).data)

    def post(self, request):
        serializer = SupplierSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SupplierDetailView(APIView):
    permission_classes = [IsAdminOrManager]

    def get_object(self, pk):
        try:
            return Supplier.objects.get(pk=pk)
        except Supplier.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SupplierSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = SupplierSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PurchaseOrderListView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        qs = PurchaseOrder.objects.select_related('supplier', 'created_by').prefetch_related('items__product')
        supplier_id = request.query_params.get('supplier_id')
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(PurchaseOrderSerializer(qs, many=True).data)

    def post(self, request):
        serializer = PurchaseOrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            po = serializer.save(created_by=request.user)
            return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderDetailView(APIView):
    permission_classes = [IsAdminOrManager]

    def get_object(self, pk):
        try:
            return PurchaseOrder.objects.select_related('supplier', 'created_by').prefetch_related('items__product').get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PurchaseOrderSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if obj.status not in ('draft', 'pending_approval'):
            return Response({'error': 'Can only edit draft or pending POs.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PurchaseOrderSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderApproveView(APIView):
    permission_classes = [IsAdminOrManager]

    def post(self, request, pk):
        try:
            po = PurchaseOrder.objects.get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if po.status not in ('draft', 'pending_approval'):
            return Response({'error': 'PO cannot be approved in its current state.'}, status=status.HTTP_400_BAD_REQUEST)

        po.status = 'approved'
        po.approved_by = request.user
        po.save(update_fields=['status', 'approved_by'])
        return Response(PurchaseOrderSerializer(po).data)


class PurchaseOrderReceiveView(APIView):
    permission_classes = [IsAdminOrManager]

    def post(self, request, pk):
        try:
            po = PurchaseOrder.objects.prefetch_related('items__product').get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if po.status != 'approved':
            return Response({'error': 'PO must be approved before receiving.'}, status=status.HTTP_400_BAD_REQUEST)

        received_items = request.data.get('items', [])
        # items: [{item_id, quantity_received}]
        for entry in received_items:
            try:
                item = po.items.get(pk=entry['item_id'])
            except Exception:
                continue
            qty = int(entry.get('quantity_received', 0))
            item.quantity_received = qty
            item.save(update_fields=['quantity_received'])

            # Update main product stock
            product = item.product
            qty_before = product.quantity
            product.quantity += qty
            product.save(update_fields=['quantity'])
            StockMovement.objects.create(
                product=product,
                movement_type='receive',
                quantity_change=qty,
                quantity_before=qty_before,
                quantity_after=product.quantity,
                reason=f'PO {po.po_number} received',
                reference_id=str(po.id),
                user=request.user,
            )

        po.status = 'received'
        po.save(update_fields=['status'])

        # Log supplier performance
        total_ordered = sum(i.quantity_ordered for i in po.items.all())
        total_received = sum(i.quantity_received for i in po.items.all())
        SupplierPerformance.objects.create(
            supplier=po.supplier,
            po=po,
            ordered_qty=total_ordered,
            received_qty=total_received,
            on_time=True,
        )

        return Response(PurchaseOrderSerializer(po).data)


class SupplierPerformanceView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request, pk):
        try:
            supplier = Supplier.objects.get(pk=pk)
        except Supplier.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        records = SupplierPerformance.objects.filter(supplier=supplier).select_related('po')
        return Response({
            'supplier': SupplierSerializer(supplier).data,
            'performance': SupplierPerformanceSerializer(records, many=True).data,
        })
