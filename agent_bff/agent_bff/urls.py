from django.urls import path, include

urlpatterns = [
    path('api/v1/agent/orders/', include('agent_orders.urls')),
]

