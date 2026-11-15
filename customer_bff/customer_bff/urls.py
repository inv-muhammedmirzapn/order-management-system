from django.http import JsonResponse
from django.urls import path, include


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'customer_bff'})


urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('api/v1/orders/', include('customer_orders.urls')),
]

