from django.contrib import admin
from .models import GiftCard, Voucher, VoucherRedemption

admin.site.register(GiftCard)
admin.site.register(Voucher)
admin.site.register(VoucherRedemption)
