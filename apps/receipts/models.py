from django.db import models


class Receipt(models.Model):
    """Stores receipt metadata for a completed sale."""

    receipt_id = models.AutoField(primary_key=True)
    sale = models.OneToOneField(
        'sales.Sale',
        on_delete=models.CASCADE,
        related_name='receipt',
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_path = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'receipts'
        verbose_name = 'Receipt'
        verbose_name_plural = 'Receipts'
        ordering = ['-generated_at']

    def __str__(self):
        return f'Receipt #{self.receipt_id} for Sale #{self.sale_id}'
