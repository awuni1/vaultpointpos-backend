from rest_framework import serializers
from .models import Shift


class ShiftSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source='cashier.full_name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True, allow_null=True)

    class Meta:
        model = Shift
        fields = '__all__'
        read_only_fields = ('cashier', 'expected_cash', 'variance', 'started_at', 'ended_at', 'status')


class ShiftStartSerializer(serializers.Serializer):
    opening_float = serializers.DecimalField(max_digits=10, decimal_places=2)
    branch_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class ShiftEndSerializer(serializers.Serializer):
    closing_cash = serializers.DecimalField(max_digits=10, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
