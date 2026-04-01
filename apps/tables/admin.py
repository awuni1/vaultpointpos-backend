from django.contrib import admin
from .models import FloorPlan, Table, TableOrder, KitchenTicket

admin.site.register(FloorPlan)
admin.site.register(Table)
admin.site.register(TableOrder)
admin.site.register(KitchenTicket)
