from django.conf import settings
from django.db import models


class FloorPlan(models.Model):
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='floor_plans')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'floor_plans'

    def __str__(self):
        return f'{self.branch.name} — {self.name}'


class Table(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('cleaning', 'Cleaning'),
    ]

    floor_plan = models.ForeignKey(FloorPlan, on_delete=models.CASCADE, related_name='tables')
    table_number = models.CharField(max_length=20)
    capacity = models.IntegerField(default=4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)

    class Meta:
        db_table = 'tables'
        unique_together = ('floor_plan', 'table_number')

    def __str__(self):
        return f'Table {self.table_number} ({self.status})'


class TableOrder(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('sent_to_kitchen', 'Sent to Kitchen'),
        ('ready', 'Ready'),
        ('billed', 'Billed'),
        ('closed', 'Closed'),
    ]

    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='orders')
    sale = models.OneToOneField('sales.Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='table_order')
    waiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    covers = models.IntegerField(default=1)
    notes = models.TextField(blank=True, default='')
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'table_orders'
        ordering = ['-opened_at']

    def __str__(self):
        return f'Order for Table {self.table.table_number}'


class KitchenTicket(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
    ]

    table_order = models.ForeignKey(TableOrder, on_delete=models.CASCADE, related_name='kitchen_tickets')
    items = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    ready_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'kitchen_tickets'
        ordering = ['created_at']

    def __str__(self):
        return f'Ticket for {self.table_order}'
