from rest_framework import serializers
from .models import GiftCard, Voucher, VoucherRedemption


class GiftCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftCard
        fields = '__all__'
        read_only_fields = ('code', 'remaining_balance', 'issued_by', 'created_at')


class VoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voucher
        fields = '__all__'
        read_only_fields = ('times_used', 'created_by', 'created_at')


class VoucherRedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoucherRedemption
        fields = '__all__'


class VoucherValidateSerializer(serializers.Serializer):
    code = serializers.CharField()
    purchase_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)


class GiftCardRedeemSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    sale_id = serializers.IntegerField(required=False)
