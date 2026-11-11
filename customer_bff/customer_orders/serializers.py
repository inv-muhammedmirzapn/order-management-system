from decimal import Decimal
from rest_framework import serializers


class OrderItemInputSerializer(serializers.Serializer):
    item_id = serializers.CharField(max_length=64, required=True)
    name = serializers.CharField(max_length=255, required=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.00'))


class CreateOrderRequestSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=64, required=True)
    customer_name = serializers.CharField(max_length=255, required=True)
    customer_email = serializers.EmailField(required=True)
    shipping_address = serializers.CharField(required=True)
    items = OrderItemInputSerializer(many=True, required=True, allow_empty=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")


class CancelOrderRequestSerializer(serializers.Serializer):
    actor_id = serializers.CharField(max_length=64, required=True)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
