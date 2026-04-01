from django.db.models import Sum, Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdmin, IsAdminOrManager
from apps.sales.models import Sale
from .models import Branch, BranchInventory, StockTransfer
from .serializers import BranchSerializer, BranchInventorySerializer, StockTransferSerializer


class BranchListView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        branches = Branch.objects.filter(is_active=True)
        return Response(BranchSerializer(branches, many=True).data)

    def post(self, request):
        serializer = BranchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BranchDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Branch.objects.get(pk=pk)
        except Branch.DoesNotExist:
            return None

    def get(self, request, pk):
        branch = self.get_object(pk)
        if not branch:
            return Response({'error': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(BranchSerializer(branch).data)

    def patch(self, request, pk):
        if request.user.role not in ['admin', 'manager']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        branch = self.get_object(pk)
        if not branch:
            return Response({'error': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = BranchSerializer(branch, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BranchInventoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            branch = Branch.objects.get(pk=pk)
        except Branch.DoesNotExist:
            return Response({'error': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)

        inventory = BranchInventory.objects.filter(branch=branch).select_related('product')
        low_stock = request.query_params.get('low_stock')
        if low_stock:
            inventory = [i for i in inventory if i.quantity <= i.reorder_level]

        return Response(BranchInventorySerializer(inventory, many=True).data)


class StockTransferView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        transfers = StockTransfer.objects.select_related(
            'from_branch', 'to_branch', 'product', 'requested_by'
        ).all()
        return Response(StockTransferSerializer(transfers, many=True).data)

    def post(self, request):
        serializer = StockTransferSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(requested_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StockTransferApproveView(APIView):
    permission_classes = [IsAdminOrManager]

    def post(self, request, pk):
        try:
            transfer = StockTransfer.objects.select_related('product', 'from_branch', 'to_branch').get(pk=pk)
        except StockTransfer.DoesNotExist:
            return Response({'error': 'Transfer not found.'}, status=status.HTTP_404_NOT_FOUND)

        if transfer.status != 'pending':
            return Response({'error': 'Transfer is not pending.'}, status=status.HTTP_400_BAD_REQUEST)

        action = request.data.get('action')  # 'approve' or 'reject'
        if action not in ('approve', 'reject'):
            return Response({'error': 'action must be "approve" or "reject".'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'approve':
            # Adjust BranchInventory for both branches
            # If no branch inventory record exists yet, seed it from the main product stock
            from_inv, _ = BranchInventory.objects.get_or_create(
                branch=transfer.from_branch,
                product=transfer.product,
                defaults={'quantity': transfer.product.quantity},
            )
            if from_inv.quantity < transfer.quantity:
                return Response({'error': 'Insufficient stock in source branch.'}, status=status.HTTP_400_BAD_REQUEST)
            from_inv.quantity -= transfer.quantity
            from_inv.save()

            to_inv, _ = BranchInventory.objects.get_or_create(
                branch=transfer.to_branch,
                product=transfer.product,
                defaults={'quantity': 0},
            )
            to_inv.quantity += transfer.quantity
            to_inv.save()
            transfer.status = 'approved'
        else:
            transfer.status = 'rejected'

        transfer.approved_by = request.user
        transfer.save()
        return Response(StockTransferSerializer(transfer).data)


class ConsolidatedReportView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        qs = Sale.objects.filter(status='completed')
        if start_date:
            qs = qs.filter(sale_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(sale_date__date__lte=end_date)

        branches = Branch.objects.filter(is_active=True)
        report = []
        for branch in branches:
            # Sales don't have branch FK in base model; report all sales total for now
            report.append({
                'branch_id': branch.id,
                'branch_name': branch.name,
                'total_sales': str(qs.aggregate(t=Sum('total_amount'))['t'] or 0),
                'transaction_count': qs.count(),
            })

        return Response({'branches': report, 'total_sales': str(qs.aggregate(t=Sum('total_amount'))['t'] or 0)})
