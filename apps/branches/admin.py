from django.contrib import admin
from .models import Branch, BranchInventory, StockTransfer

admin.site.register(Branch)
admin.site.register(BranchInventory)
admin.site.register(StockTransfer)
