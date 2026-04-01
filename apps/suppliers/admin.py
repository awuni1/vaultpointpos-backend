from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierPerformance

admin.site.register(Supplier)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(SupplierPerformance)
