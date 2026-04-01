from rest_framework import serializers
from .models import SalesForecast


class SalesForecastSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True, allow_null=True)

    class Meta:
        model = SalesForecast
        fields = '__all__'
