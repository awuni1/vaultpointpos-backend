from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories."""

    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['category_id', 'name', 'description', 'product_count', 'created_at']
        read_only_fields = ['category_id', 'created_at']

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()

    def validate_name(self, value):
        instance = self.instance
        qs = Category.objects.filter(name__iexact=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A category with this name already exists.')
        return value


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for products."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    profit_margin = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'product_id', 'product_name', 'category', 'category_name',
            'price', 'cost_price', 'quantity', 'barcode', 'reorder_level',
            'is_active', 'image_url', 'is_low_stock', 'profit_margin',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['product_id', 'created_at', 'updated_at', 'is_low_stock', 'profit_margin']

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Price cannot be negative.')
        return value

    def validate_cost_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Cost price cannot be negative.')
        return value

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError('Quantity cannot be negative.')
        return value

    def validate_reorder_level(self, value):
        if value < 0:
            raise serializers.ValidationError('Reorder level cannot be negative.')
        return value

    def validate_barcode(self, value):
        if not value:
            return value
        instance = self.instance
        qs = Product.objects.filter(barcode=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A product with this barcode already exists.')
        return value


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'product_id', 'product_name', 'category', 'category_name',
            'price', 'quantity', 'barcode', 'reorder_level',
            'is_active', 'is_low_stock', 'image_url',
        ]
