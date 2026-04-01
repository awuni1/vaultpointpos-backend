from django.db import models


class Category(models.Model):
    """Product category model."""

    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model representing items sold at the POS."""

    product_id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=255)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.IntegerField(default=0)
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)
    reorder_level = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True)
    image_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['product_name']

    def __str__(self):
        return f'{self.product_name} (${self.price})'

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    @property
    def profit_margin(self):
        if self.cost_price and self.price > 0:
            return ((self.price - self.cost_price) / self.price) * 100
        return None
