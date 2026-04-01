from rest_framework import serializers


class DailySalesSerializer(serializers.Serializer):
    """Serializer for daily sales report data."""

    date = serializers.DateField()
    total_sales = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_tax = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    completed_sales = serializers.IntegerField()
    voided_sales = serializers.IntegerField()
    refunded_sales = serializers.IntegerField()
    payment_breakdown = serializers.DictField()
    top_products = serializers.ListField()
    hourly_breakdown = serializers.ListField()


class WeeklySalesSerializer(serializers.Serializer):
    """Serializer for weekly sales report."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_sales = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_daily_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    daily_breakdown = serializers.ListField()
    payment_breakdown = serializers.DictField()


class MonthlySalesSerializer(serializers.Serializer):
    """Serializer for monthly sales report."""

    year = serializers.IntegerField()
    month = serializers.IntegerField()
    month_name = serializers.CharField()
    total_sales = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_tax = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_transaction_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    daily_breakdown = serializers.ListField()
    payment_breakdown = serializers.DictField()


class ProductPerformanceSerializer(serializers.Serializer):
    """Serializer for product performance report."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    products = serializers.ListField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)


class InventoryReportSerializer(serializers.Serializer):
    """Serializer for inventory valuation report."""

    generated_at = serializers.DateTimeField()
    total_products = serializers.IntegerField()
    active_products = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    out_of_stock_count = serializers.IntegerField()
    total_inventory_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_cost_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    categories = serializers.ListField()
    low_stock_products = serializers.ListField()


class CashierPerformanceSerializer(serializers.Serializer):
    """Serializer for cashier performance report."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    cashiers = serializers.ListField()


class PaymentMethodReportSerializer(serializers.Serializer):
    """Serializer for payment method breakdown report."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transactions = serializers.IntegerField()
    payment_methods = serializers.ListField()
