from django.urls import path
from .views import (
    CustomerOrderListCreateView,
    CustomerOrderDetailView,
    CustomerOrderCancelView,
)

urlpatterns = [
    path('create/', CustomerOrderListCreateView.as_view(), name='customer-order-create-alias'),
    path('<str:order_id>/', CustomerOrderDetailView.as_view(), name='customer-order-detail'),
    path('<str:order_id>/cancel/', CustomerOrderCancelView.as_view(), name='customer-order-cancel'),
]

