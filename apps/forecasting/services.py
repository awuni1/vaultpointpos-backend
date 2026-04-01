"""
Simple linear regression forecasting using numpy.
Uses last 90 days of sales data per product.
"""
from datetime import timedelta

import numpy as np
from django.utils import timezone


def _linear_regression(x, y):
    """Return (slope, intercept) for arrays x, y."""
    n = len(x)
    if n < 2:
        return 0.0, float(y[0]) if n == 1 else 0.0
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    x_mean, y_mean = x_arr.mean(), y_arr.mean()
    denom = ((x_arr - x_mean) ** 2).sum()
    if denom == 0:
        return 0.0, y_mean
    slope = ((x_arr - x_mean) * (y_arr - y_mean)).sum() / denom
    intercept = y_mean - slope * x_mean
    return float(slope), float(intercept)


def forecast_product(product_id, days=7):
    from django.db.models import Sum
    from apps.sales.models import SaleItem
    from apps.products.models import Product
    from .models import SalesForecast

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return []

    today = timezone.now().date()
    ninety_days_ago = today - timedelta(days=90)

    daily_sales = (
        SaleItem.objects
        .filter(product=product, sale__sale_date__date__gte=ninety_days_ago, sale__status='completed')
        .values('sale__sale_date__date')
        .annotate(total_qty=Sum('quantity'), total_rev=Sum('line_total'))
        .order_by('sale__sale_date__date')
    )

    if not daily_sales:
        return []

    data = list(daily_sales)
    x = list(range(len(data)))
    y_qty = [float(d['total_qty']) for d in data]
    y_rev = [float(d['total_rev']) for d in data]

    slope_qty, intercept_qty = _linear_regression(x, y_qty)
    slope_rev, intercept_rev = _linear_regression(x, y_rev)

    n = len(x)
    forecasts = []
    for i in range(1, days + 1):
        pred_x = n + i
        pred_qty = max(0, slope_qty * pred_x + intercept_qty)
        pred_rev = max(0, slope_rev * pred_x + intercept_rev)
        fdate = today + timedelta(days=i)

        forecast, _ = SalesForecast.objects.update_or_create(
            product=product,
            forecast_date=fdate,
            model_version='linear_v1',
            defaults={
                'predicted_quantity': round(pred_qty, 2),
                'predicted_revenue': round(pred_rev, 2),
                'confidence_score': min(0.9999, max(0, round(1 - (0.05 * i), 4))),
            }
        )
        forecasts.append(forecast)

    return forecasts


def forecast_store(days=7):
    from django.db.models import Sum
    from apps.sales.models import Sale
    from .models import SalesForecast
    from datetime import timedelta

    today = timezone.now().date()
    ninety_days_ago = today - timedelta(days=90)

    daily = (
        Sale.objects
        .filter(status='completed', sale_date__date__gte=ninety_days_ago)
        .values('sale_date__date')
        .annotate(total=Sum('total_amount'))
        .order_by('sale_date__date')
    )

    data = list(daily)
    if not data:
        return []

    x = list(range(len(data)))
    y = [float(d['total']) for d in data]
    slope, intercept = _linear_regression(x, y)
    n = len(x)
    forecasts = []
    for i in range(1, days + 1):
        pred_x = n + i
        pred_rev = max(0, slope * pred_x + intercept)
        fdate = today + timedelta(days=i)

        forecast, _ = SalesForecast.objects.update_or_create(
            product=None,
            forecast_date=fdate,
            model_version='linear_v1',
            defaults={
                'predicted_quantity': 0,
                'predicted_revenue': round(pred_rev, 2),
                'confidence_score': min(0.9999, max(0, round(1 - (0.05 * i), 4))),
            }
        )
        forecasts.append(forecast)
    return forecasts
