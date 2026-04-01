from decimal import Decimal

from rest_framework import serializers

from apps.products.models import Product
from .models import Sale, SaleItem, TransactionLog


class SaleItemCreateSerializer(serializers.Serializer):
    """Serializer for individual items when creating a sale."""

    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    discount_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        min_value=Decimal('0'), max_value=Decimal('100'),
    )

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(product_id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError(f'Product with ID {value} not found or inactive.')
        return value


class SaleItemSerializer(serializers.ModelSerializer):
    """Serializer for reading sale item data."""

    product_name = serializers.CharField(source='product.product_name', read_only=True)
    product_barcode = serializers.CharField(source='product.barcode', read_only=True)

    class Meta:
        model = SaleItem
        fields = [
            'sale_item_id', 'product', 'product_name', 'product_barcode',
            'quantity', 'unit_price', 'discount_pct', 'line_total',
        ]
        read_only_fields = ['sale_item_id', 'line_total']


class SaleCreateSerializer(serializers.Serializer):
    """Serializer for creating a new sale."""

    items = SaleItemCreateSerializer(many=True, min_length=1)
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    payment_method = serializers.ChoiceField(choices=Sale.PAYMENT_METHOD_CHOICES)
    tax_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        min_value=Decimal('0'), max_value=Decimal('100'),
    )
    discount_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        min_value=Decimal('0'),
    )
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_customer_id(self, value):
        if value is None:
            return value
        from apps.customers.models import Customer
        try:
            Customer.objects.get(customer_id=value)
        except Customer.DoesNotExist:
            raise serializers.ValidationError(f'Customer with ID {value} not found.')
        return value

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('At least one item is required.')

        # Check for duplicate products
        product_ids = [item['product_id'] for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                'Duplicate products are not allowed. Combine quantities instead.'
            )

        # Check stock availability
        errors = []
        for item in items:
            try:
                product = Product.objects.get(product_id=item['product_id'], is_active=True)
                if product.quantity < item['quantity']:
                    errors.append(
                        f'Insufficient stock for "{product.product_name}". '
                        f'Available: {product.quantity}, Requested: {item["quantity"]}'
                    )
            except Product.DoesNotExist:
                errors.append(f'Product with ID {item["product_id"]} not found.')

        if errors:
            raise serializers.ValidationError(errors)

        return items


class SaleSerializer(serializers.ModelSerializer):
    """Full serializer for reading sale data."""

    items = SaleItemSerializer(many=True, read_only=True)
    cashier_name = serializers.CharField(source='user.full_name', read_only=True)
    cashier_username = serializers.CharField(source='user.username', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)

    class Meta:
        model = Sale
        fields = [
            'sale_id', 'sale_date', 'user', 'cashier_name', 'cashier_username',
            'customer', 'customer_name', 'items',
            'subtotal', 'discount_amount', 'tax_amount', 'tax_rate',
            'total_amount', 'payment_method', 'status', 'notes',
        ]
        read_only_fields = [
            'sale_id', 'sale_date', 'subtotal', 'tax_amount', 'total_amount',
        ]


class SaleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for sale list views."""

    cashier_name = serializers.CharField(source='user.full_name', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            'sale_id', 'sale_date', 'cashier_name', 'customer_name',
            'total_amount', 'payment_method', 'status', 'item_count',
        ]

    def get_item_count(self, obj):
        return obj.items.count()


class TransactionLogSerializer(serializers.ModelSerializer):
    """Serializer for transaction log entries."""

    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = TransactionLog
        fields = [
            'log_id', 'user', 'username', 'action', 'entity_type',
            'entity_id', 'details', 'ip_address', 'created_at',
        ]
        read_only_fields = ['log_id', 'created_at']
