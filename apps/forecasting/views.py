from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager, IsAdmin
from apps.products.models import Product
from .models import SalesForecast
from .serializers import SalesForecastSerializer
from . import services


class ProductForecastView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get('days', 7))
        forecasts = services.forecast_product(pk, days=days)
        return Response({
            'product_id': pk,
            'product_name': product.product_name,
            'forecasts': SalesForecastSerializer(forecasts, many=True).data,
        })


class StoreForecastView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        days = int(request.query_params.get('days', 7))
        today = timezone.now().date()
        # Return cached forecasts if they exist for today
        cached = SalesForecast.objects.filter(
            product__isnull=True,
            forecast_date__gte=today,
            created_at__date=today,
        ).order_by('forecast_date')
        if cached.exists():
            return Response(SalesForecastSerializer(cached, many=True).data)

        forecasts = services.forecast_store(days=days)
        return Response(SalesForecastSerializer(forecasts, many=True).data)


class LowStockForecastView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        """Products predicted to run out before next delivery."""
        today = timezone.now().date()
        # Find products where current stock < predicted quantity for next 7 days
        at_risk = []
        products = Product.objects.filter(is_active=True, quantity__gt=0)
        for product in products:
            forecasts = SalesForecast.objects.filter(
                product=product,
                forecast_date__gte=today,
            ).order_by('forecast_date')[:7]
            if not forecasts.exists():
                continue
            total_predicted = sum(float(f.predicted_quantity) for f in forecasts)
            if total_predicted > product.quantity:
                days_until_stockout = 0
                running = float(product.quantity)
                for f in forecasts:
                    running -= float(f.predicted_quantity)
                    days_until_stockout += 1
                    if running <= 0:
                        break
                at_risk.append({
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'current_stock': product.quantity,
                    'reorder_level': product.reorder_level,
                    'predicted_demand_7d': round(total_predicted, 1),
                    'estimated_stockout_in_days': days_until_stockout,
                })

        return Response({
            'at_risk_count': len(at_risk),
            'products_at_risk': sorted(at_risk, key=lambda x: x['estimated_stockout_in_days']),
        })


class RunForecastView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        days = int(request.data.get('days', 7))
        products = Product.objects.filter(is_active=True)
        count = 0
        for product in products:
            results = services.forecast_product(product.pk, days=days)
            count += len(results)

        store_results = services.forecast_store(days=days)
        return Response({
            'message': 'Forecasts recomputed.',
            'product_forecasts_created': count,
            'store_forecasts_created': len(store_results),
        })
