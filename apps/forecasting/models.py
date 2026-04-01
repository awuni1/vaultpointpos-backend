from django.db import models


class SalesForecast(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, null=True, blank=True, related_name='forecasts')
    forecast_date = models.DateField()
    predicted_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    predicted_revenue = models.DecimalField(max_digits=10, decimal_places=2)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    model_version = models.CharField(max_length=30, default='linear_v1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_forecasts'
        unique_together = ('product', 'forecast_date', 'model_version')
        ordering = ['forecast_date']

    def __str__(self):
        product_name = self.product.product_name if self.product else 'Store-wide'
        return f'Forecast {product_name} on {self.forecast_date}: qty={self.predicted_quantity}'
