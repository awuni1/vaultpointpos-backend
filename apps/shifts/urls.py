from django.urls import path
from . import views

urlpatterns = [
    path('', views.ShiftListView.as_view(), name='shift-list'),
    path('start/', views.ShiftStartView.as_view(), name='shift-start'),
    path('<int:pk>/', views.ShiftDetailView.as_view(), name='shift-detail'),
    path('<int:pk>/end/', views.ShiftEndView.as_view(), name='shift-end'),
    path('<int:pk>/reconciliation/', views.ShiftReconciliationView.as_view(), name='shift-reconciliation'),
]
