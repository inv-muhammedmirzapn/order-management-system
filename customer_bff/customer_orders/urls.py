from django.urls import path
from .views import (
    CustomerOrderListCreateView,
    CustomerOrderDetailView,
    CustomerOrderCancelView,
)

urlpatterns = [
    path('', CustomerOrderListCreateView.as_view(), name='customer-order-list-create'),
    path('<str:order_id>/', CustomerOrderDetailView.as_view(), name='customer-order-detail'),
    path('<str:order_id>/cancel/', CustomerOrderCancelView.as_view(), name='customer-order-cancel'),
]

