from rest_framework import serializers

from apps.sales.serializers import SaleItemSerializer
from apps.sales.models import Sale
from .models import Receipt


class ReceiptItemSerializer(serializers.Serializer):
    """Serializer for a single receipt line item."""

    product_id = serializers.IntegerField(source='product.product_id')
    product_name = serializers.CharField(source='product.product_name')
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2)


class ReceiptSerializer(serializers.Serializer):
    """Full receipt data formatted for display or printing."""

    receipt_id = serializers.IntegerField(allow_null=True)
    sale_id = serializers.IntegerField()
    sale_date = serializers.DateTimeField()
    generated_at = serializers.DateTimeField(allow_null=True)

    # Cashier info
    cashier_name = serializers.CharField()
    cashier_username = serializers.CharField()

    # Customer info
    customer_id = serializers.IntegerField(allow_null=True)
    customer_name = serializers.CharField(allow_null=True)
    customer_phone = serializers.CharField(allow_null=True)
    loyalty_points_earned = serializers.IntegerField()

    # Items
    items = ReceiptItemSerializer(many=True)

    # Totals
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_method = serializers.CharField()
    status = serializers.CharField()

    # Business info (configurable)
    business_name = serializers.CharField()
    business_address = serializers.CharField()
    business_phone = serializers.CharField()


class ReceiptModelSerializer(serializers.ModelSerializer):
    """Basic serializer for the Receipt model."""

    class Meta:
        model = Receipt
        fields = ['receipt_id', 'sale', 'generated_at', 'pdf_path']
        read_only_fields = ['receipt_id', 'generated_at']
