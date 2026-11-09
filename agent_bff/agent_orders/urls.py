from django.urls import path
from .views import (
    OrderListView,
    OrderDetailView,
    AssignOrderView,
    StartProcessingView,
    UpdateStatusView,
    CompleteOrderView,
    OrderActivitiesView,
)

urlpatterns = [
    path('', OrderListView.as_view(), name='agent-order-list'),
    path('<str:order_id>/', OrderDetailView.as_view(), name='agent-order-detail'),
    path('<str:order_id>/assign/', AssignOrderView.as_view(), name='agent-order-assign'),
    path('<str:order_id>/start-processing/', StartProcessingView.as_view(), name='agent-order-start-processing'),
    path('<str:order_id>/update-status/', UpdateStatusView.as_view(), name='agent-order-update-status'),
    path('<str:order_id>/complete/', CompleteOrderView.as_view(), name='agent-order-complete'),
    path('<str:order_id>/activities/', OrderActivitiesView.as_view(), name='agent-order-activities'),
]

