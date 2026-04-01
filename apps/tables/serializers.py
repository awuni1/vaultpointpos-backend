from rest_framework import serializers
from .models import FloorPlan, Table, TableOrder, KitchenTicket


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = '__all__'


class FloorPlanSerializer(serializers.ModelSerializer):
    tables = TableSerializer(many=True, read_only=True)

    class Meta:
        model = FloorPlan
        fields = '__all__'


class KitchenTicketSerializer(serializers.ModelSerializer):
    table_number = serializers.CharField(source='table_order.table.table_number', read_only=True)

    class Meta:
        model = KitchenTicket
        fields = '__all__'


class TableOrderSerializer(serializers.ModelSerializer):
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    waiter_name = serializers.CharField(source='waiter.full_name', read_only=True)
    kitchen_tickets = KitchenTicketSerializer(many=True, read_only=True)

    class Meta:
        model = TableOrder
        fields = '__all__'
        read_only_fields = ('opened_at', 'closed_at', 'waiter')
