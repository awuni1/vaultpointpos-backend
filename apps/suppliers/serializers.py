from rest_framework import serializers
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierPerformance


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'
        read_only_fields = ('created_at',)


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'
        read_only_fields = ('id', 'po', 'line_total', 'quantity_received')


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = '__all__'
        read_only_fields = ('po_number', 'total_amount', 'approved_by', 'created_by', 'created_at', 'updated_at')


class PurchaseOrderCreateSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = ('supplier', 'branch', 'notes', 'expected_delivery', 'items')

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        po = PurchaseOrder.objects.create(**validated_data)
        total = 0
        for item_data in items_data:
            item = PurchaseOrderItem.objects.create(po=po, **item_data)
            total += item.line_total
        po.total_amount = total
        po.save(update_fields=['total_amount'])
        return po


class SupplierPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierPerformance
        fields = '__all__'
