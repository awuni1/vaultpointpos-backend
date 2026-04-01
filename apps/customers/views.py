from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from .models import Customer
from .serializers import CustomerListSerializer, CustomerSerializer, CustomerUpdateSerializer


class CustomerListView(APIView):
    """List all customers or create a new one."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Customer.objects.all()

        # Search by name, phone, or email
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(full_name__icontains=search) | \
                       queryset.filter(phone__icontains=search) | \
                       queryset.filter(email__icontains=search)
            queryset = queryset.distinct()

        queryset = queryset.order_by('full_name')
        serializer = CustomerListSerializer(queryset, many=True)
        return Response(
            {'count': queryset.count(), 'results': serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = CustomerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        customer = serializer.save()
        return Response(
            CustomerSerializer(customer).data,
            status=status.HTTP_201_CREATED
        )


class CustomerDetailView(APIView):
    """Retrieve or update a specific customer."""

    permission_classes = [IsAuthenticated]

    def get_object(self, customer_id):
        try:
            return Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return None

    def get(self, request, customer_id):
        customer = self.get_object(customer_id)
        if not customer:
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)

    def put(self, request, customer_id):
        customer = self.get_object(customer_id)
        if not customer:
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CustomerUpdateSerializer(customer, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)

    def patch(self, request, customer_id):
        customer = self.get_object(customer_id)
        if not customer:
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CustomerUpdateSerializer(customer, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)

    def delete(self, request, customer_id):
        customer = self.get_object(customer_id)
        if not customer:
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role not in ['admin', 'manager']:
            return Response(
                {'error': 'Only managers or admins can delete customers.'},
                status=status.HTTP_403_FORBIDDEN
            )

        customer_name = customer.full_name
        customer.delete()
        return Response(
            {'message': f'Customer "{customer_name}" has been deleted.'},
            status=status.HTTP_200_OK
        )


class CustomerPurchaseHistoryView(APIView):
    """Get a customer's full purchase history."""

    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        from apps.sales.models import Sale
        from apps.sales.serializers import SaleListSerializer

        sales = Sale.objects.filter(
            customer=customer
        ).select_related('user').prefetch_related('items__product').order_by('-sale_date')

        from apps.sales.serializers import SaleListSerializer
        serializer = SaleListSerializer(sales, many=True)

        return Response(
            {
                'customer': CustomerSerializer(customer).data,
                'purchase_history': serializer.data,
                'total_purchases': sales.count(),
            },
            status=status.HTTP_200_OK
        )


class TopCustomersView(APIView):
    """Get the top 10 customers by total spending."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        top_customers = Customer.objects.order_by('-total_spent')[:10]
        serializer = CustomerSerializer(top_customers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomerExportView(APIView):
    """Export all customers as a CSV file."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        import csv
        from django.http import HttpResponse

        customers = Customer.objects.all().order_by('full_name')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="customers.csv"'

        writer = csv.writer(response)
        writer.writerow(['id', 'full_name', 'phone', 'email', 'address', 'birthday', 'loyalty_points', 'total_spent', 'registered_at'])

        for c in customers:
            writer.writerow([
                c.customer_id,
                c.full_name,
                c.phone or '',
                c.email or '',
                c.address or '',
                str(c.birthday) if c.birthday else '',
                c.loyalty_points,
                float(c.total_spent),
                c.registered_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])

        return response
