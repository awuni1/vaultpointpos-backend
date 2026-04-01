from rest_framework import serializers
from .models import Branch, BranchInventory, StockTransfer


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'
        read_only_fields = ('created_at',)


class BranchInventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = BranchInventory
        fields = '__all__'

    def get_is_low_stock(self, obj):
        return obj.quantity <= obj.reorder_level


class StockTransferSerializer(serializers.ModelSerializer):
    from_branch_name = serializers.CharField(source='from_branch.name', read_only=True)
    to_branch_name = serializers.CharField(source='to_branch.name', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.full_name', read_only=True)

    class Meta:
        model = StockTransfer
        fields = '__all__'
        read_only_fields = ('status', 'approved_by', 'created_at', 'updated_at')
