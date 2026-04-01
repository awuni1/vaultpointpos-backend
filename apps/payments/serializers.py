from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment records."""

    sale_total = serializers.DecimalField(
        source='sale.total_amount', max_digits=12, decimal_places=2, read_only=True
    )
    sale_date = serializers.DateTimeField(source='sale.sale_date', read_only=True)
    cashier_name = serializers.CharField(source='sale.user.full_name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'payment_id', 'sale', 'sale_total', 'sale_date', 'cashier_name',
            'payment_method', 'amount', 'reference_number', 'card_last_four',
            'amount_tendered', 'change_due', 'created_at',
        ]
        read_only_fields = ['payment_id', 'created_at']


class CashReconciliationSerializer(serializers.Serializer):
    """Serializer for daily cash reconciliation data."""

    date = serializers.DateField()
    expected_cash = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_sales_count = serializers.IntegerField()
    total_sales_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    cash_sales_count = serializers.IntegerField()
    mobile_money_count = serializers.IntegerField()
    mobile_money_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    card_count = serializers.IntegerField()
    card_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    refunds_count = serializers.IntegerField()
    refunds_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
