from django.urls import path
from . import views

urlpatterns = [
    path('', views.TableListCreateView.as_view(), name='table-list-create'),
    path('floor-plan/<int:branch_id>/', views.FloorPlanView.as_view(), name='floor-plan'),
    path('<int:pk>/status/', views.TableStatusUpdateView.as_view(), name='table-status'),
    path('<int:table_id>/order/', views.TableOrderCreateView.as_view(), name='table-order-create'),
    path('orders/<int:pk>/', views.TableOrderDetailView.as_view(), name='table-order-detail'),
    path('orders/<int:pk>/split/', views.SplitBillView.as_view(), name='split-bill'),
    path('kitchen/', views.KitchenDisplayView.as_view(), name='kitchen-display'),
    path('kitchen/<int:pk>/', views.KitchenTicketUpdateView.as_view(), name='kitchen-ticket-update'),
]
