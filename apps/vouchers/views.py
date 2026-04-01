from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminOrManager
from .models import GiftCard, Voucher, VoucherRedemption
from .serializers import (
    GiftCardSerializer, VoucherSerializer, VoucherRedemptionSerializer,
    VoucherValidateSerializer, GiftCardRedeemSerializer,
)


class GiftCardCreateView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        cards = GiftCard.objects.select_related('issued_by', 'customer').all()
        return Response(GiftCardSerializer(cards, many=True).data)

    def post(self, request):
        serializer = GiftCardSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(issued_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GiftCardBalanceView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, code):
        try:
            card = GiftCard.objects.get(code=code.upper())
        except GiftCard.DoesNotExist:
            return Response({'error': 'Gift card not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'code': card.code,
            'remaining_balance': str(card.remaining_balance),
            'is_active': card.is_active,
            'expires_at': card.expires_at,
        })


class GiftCardRedeemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, code):
        try:
            card = GiftCard.objects.get(code=code.upper())
        except GiftCard.DoesNotExist:
            return Response({'error': 'Gift card not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not card.is_active:
            return Response({'error': 'Gift card is inactive.'}, status=status.HTTP_400_BAD_REQUEST)
        if card.expires_at and card.expires_at < timezone.now().date():
            return Response({'error': 'Gift card has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = GiftCardRedeemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data['amount']
        if amount > card.remaining_balance:
            return Response(
                {'error': f'Insufficient balance. Available: {card.remaining_balance}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        card.remaining_balance -= amount
        if card.remaining_balance == 0:
            card.is_active = False
        card.save(update_fields=['remaining_balance', 'is_active'])

        return Response({
            'message': 'Gift card redeemed successfully.',
            'amount_deducted': str(amount),
            'remaining_balance': str(card.remaining_balance),
        })


class VoucherViewSet(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        vouchers = Voucher.objects.all()
        active = request.query_params.get('active')
        if active == 'true':
            vouchers = vouchers.filter(is_active=True)
        return Response(VoucherSerializer(vouchers, many=True).data)

    def post(self, request):
        serializer = VoucherSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VoucherDetailView(APIView):
    permission_classes = [IsAdminOrManager]

    def get_object(self, pk):
        try:
            return Voucher.objects.get(pk=pk)
        except Voucher.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(VoucherSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = VoucherSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class VoucherValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VoucherValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code'].upper()
        purchase_amount = serializer.validated_data.get('purchase_amount', 0)

        try:
            voucher = Voucher.objects.get(code=code)
        except Voucher.DoesNotExist:
            return Response({'valid': False, 'error': 'Voucher not found.'}, status=status.HTTP_404_NOT_FOUND)

        valid, message = voucher.is_valid()
        if not valid:
            return Response({'valid': False, 'error': message})

        if purchase_amount < voucher.minimum_purchase:
            return Response({
                'valid': False,
                'error': f'Minimum purchase of {voucher.minimum_purchase} required.',
            })

        discount_amount = 0
        if voucher.voucher_type == 'percentage':
            discount_amount = float(purchase_amount) * float(voucher.discount_value) / 100
        elif voucher.voucher_type == 'flat_amount':
            discount_amount = min(float(voucher.discount_value), float(purchase_amount))

        return Response({
            'valid': True,
            'voucher': VoucherSerializer(voucher).data,
            'discount_amount': round(discount_amount, 2),
        })


class VoucherRedeemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '').upper()
        sale_id = request.data.get('sale_id')
        amount_discounted = request.data.get('amount_discounted', 0)

        try:
            voucher = Voucher.objects.get(code=code)
        except Voucher.DoesNotExist:
            return Response({'error': 'Voucher not found.'}, status=status.HTTP_404_NOT_FOUND)

        valid, message = voucher.is_valid()
        if not valid:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

        from apps.sales.models import Sale
        try:
            sale = Sale.objects.get(sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found.'}, status=status.HTTP_404_NOT_FOUND)

        redemption = VoucherRedemption.objects.create(
            voucher=voucher,
            sale=sale,
            amount_discounted=amount_discounted,
            redeemed_by=request.user,
        )
        voucher.times_used += 1
        if voucher.times_used >= voucher.max_uses:
            voucher.is_active = False
        voucher.save(update_fields=['times_used', 'is_active'])

        return Response(VoucherRedemptionSerializer(redemption).data, status=status.HTTP_201_CREATED)
