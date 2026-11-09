from django.urls import path, include

urlpatterns = [
    path('api/v1/orders/', include('customer_orders.urls')),
]

