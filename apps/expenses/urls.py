from django.urls import path
from . import views

urlpatterns = [
    path('', views.ExpenseListView.as_view(), name='expense-list'),
    path('<int:pk>/', views.ExpenseDetailView.as_view(), name='expense-detail'),
    path('categories/', views.ExpenseCategoryListView.as_view(), name='expense-category-list'),
    path('categories/<int:pk>/', views.ExpenseCategoryDetailView.as_view(), name='expense-category-detail'),
    path('summary/', views.ExpenseSummaryView.as_view(), name='expense-summary'),
    path('profit/', views.ProfitReportView.as_view(), name='profit-report'),
]
