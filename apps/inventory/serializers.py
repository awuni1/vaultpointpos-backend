from rest_framework import serializers

from apps.products.serializers import ProductListSerializer
from apps.products.models import Product
from .models import StockMovement, SupplierDelivery


class StockMovementSerializer(serializers.ModelSerializer):
    """Serializer for stock movement records."""

    product_name = serializers.CharField(source='product.product_name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'movement_id', 'product', 'product_name', 'movement_type',
            'quantity_change', 'quantity_before', 'quantity_after',
            'reason', 'reference_id', 'user', 'user_username', 'created_at',
        ]
        read_only_fields = [
            'movement_id', 'quantity_before', 'quantity_after',
            'user', 'created_at',
        ]


class StockAdjustmentSerializer(serializers.Serializer):
    """Serializer for manually adjusting stock levels."""

    product_id = serializers.IntegerField()
    quantity_change = serializers.IntegerField()
    reason = serializers.CharField(max_length=500)

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(product_id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError('Product not found or inactive.')
        return value

    def validate(self, attrs):
        product_id = attrs.get('product_id')
        quantity_change = attrs.get('quantity_change')

        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError({'product_id': 'Product not found.'})

        new_quantity = product.quantity + quantity_change
        if new_quantity < 0:
            raise serializers.ValidationError(
                {
                    'quantity_change': (
                        f'Cannot reduce stock below zero. Current stock: {product.quantity}, '
                        f'Requested change: {quantity_change}'
                    )
                }
            )

        attrs['product'] = product
        return attrs


class ReceiveStockSerializer(serializers.ModelSerializer):
    """Serializer for receiving supplier deliveries."""

    class Meta:
        model = SupplierDelivery
        fields = [
            'delivery_id', 'product', 'supplier_name', 'quantity_received',
            'unit_cost', 'delivery_date', 'notes', 'user', 'created_at',
        ]
        read_only_fields = ['delivery_id', 'user', 'created_at']

    def validate_quantity_received(self, value):
        if value <= 0:
            raise serializers.ValidationError('Quantity received must be greater than zero.')
        return value

    def validate_unit_cost(self, value):
        if value < 0:
            raise serializers.ValidationError('Unit cost cannot be negative.')
        return value

    def validate_product(self, value):
        if not value.is_active:
            raise serializers.ValidationError('Cannot receive stock for an inactive product.')
        return value


class SupplierDeliverySerializer(serializers.ModelSerializer):
    """Serializer for viewing supplier deliveries."""

    product_name = serializers.CharField(source='product.product_name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SupplierDelivery
        fields = [
            'delivery_id', 'product', 'product_name', 'supplier_name',
            'quantity_received', 'unit_cost', 'delivery_date', 'notes',
            'user', 'user_username', 'created_at',
        ]
        read_only_fields = ['delivery_id', 'user', 'created_at']


class InventoryItemSerializer(serializers.ModelSerializer):
    """Serializer for inventory list view (products with stock info)."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'product_id', 'product_name', 'category', 'category_name',
            'price', 'cost_price', 'quantity', 'barcode', 'reorder_level',
            'is_active', 'is_low_stock',
        ]
