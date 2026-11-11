import hashlib
import json
import logging
import grpc
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from generated import customer_order_pb2
from .grpc_client import get_order_stub, proto_to_dict, GrpcClientError
from .serializers import CreateOrderRequestSerializer, CancelOrderRequestSerializer

logger = logging.getLogger(__name__)

IDEMPOTENCY_CACHE_TTL = 120  # 2 minutes deduplication window
LOCK_TIMEOUT = 15            # Concurrent request lock timeout


def _compute_idempotency_info(request, validated_data: dict):
    """
    Extract or generate idempotency key.
    Returns: (cache_key, lock_key, is_explicit)
    """
    explicit_key = (
        request.headers.get("Idempotency-Key")
        or request.headers.get("X-Idempotency-Key")
        or validated_data.get("idempotency_key")
    )
    if explicit_key and str(explicit_key).strip():
        key = str(explicit_key).strip()
        return f"order_idem_key:{key}", f"order_lock_key:{key}", True

    # Compute deterministic fingerprint from payload
    normalized_items = sorted(
        [
            (
                str(item.get("item_id", "")).strip(),
                int(item.get("quantity", 1)),
                f"{float(item.get('unit_price', 0)):.2f}",
            )
            for item in validated_data.get("items", [])
        ],
        key=lambda x: x[0],
    )
    fingerprint_dict = {
        "customer_id": str(validated_data.get("customer_id", "")).strip(),
        "shipping_address": str(validated_data.get("shipping_address", "")).strip().lower(),
        "items": normalized_items,
    }
    raw_bytes = json.dumps(fingerprint_dict, sort_keys=True).encode("utf-8")
    payload_hash = hashlib.sha256(raw_bytes).hexdigest()
    return f"order_idem_hash:{payload_hash}", f"order_lock_hash:{payload_hash}", False


class CustomerOrderListCreateView(APIView):
    """
    POST /api/v1/orders/ -> Create a new order via gRPC CreateOrder.
    Includes idempotency protection and duplicate order prevention.
    """
    def post(self, request):
        serializer = CreateOrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cache_key, lock_key, is_explicit = _compute_idempotency_info(request, data)

        # 1. Check if order response is already cached (duplicate request)
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            logger.info("Duplicate order request detected for key: %s (explicit=%s)", cache_key, is_explicit)
            if is_explicit:
                response = Response(cached_response, status=status.HTTP_200_OK)
                response["Idempotent-Replay"] = "true"
                return response
            return Response(
                {
                    "error": "Duplicate order detected. An order with identical details was recently placed.",
                    "order_id": cached_response.get("order", {}).get("id", ""),
                    "order": cached_response.get("order", {}),
                },
                status=status.HTTP_409_CONFLICT,
            )

        # 2. Acquire concurrency lock to prevent simultaneous duplicate processing
        acquired = cache.add(lock_key, "IN_PROGRESS", timeout=LOCK_TIMEOUT)
        if not acquired:
            logger.warning("Concurrent order request in-progress for key: %s", lock_key)
            return Response(
                {
                    "error": "An identical order request is currently being processed. Please wait.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            stub = get_order_stub()
            grpc_items = [
                customer_order_pb2.OrderItemInput(
                    item_id=item["item_id"],
                    name=item["name"],
                    quantity=item["quantity"],
                    unit_price=float(item["unit_price"]),
                )
                for item in data["items"]
            ]

            grpc_request = customer_order_pb2.CreateOrderRequest(
                customer_id=data["customer_id"],
                customer_name=data["customer_name"],
                customer_email=data["customer_email"],
                shipping_address=data["shipping_address"],
                items=grpc_items,
                notes=data.get("notes", ""),
            )

            grpc_response = stub.CreateOrder(grpc_request)
            result = {
                "message": grpc_response.message,
                "order": proto_to_dict(grpc_response.order),
            }

            cache.set(cache_key, result, timeout=IDEMPOTENCY_CACHE_TTL)
            return Response(result, status=status.HTTP_201_CREATED)

        except grpc.RpcError as e:
            raise GrpcClientError(e)
        finally:
            cache.delete(lock_key)


class CustomerOrderDetailView(APIView):
    """
    GET /api/v1/orders/<order_id>/ -> Fetch order details via gRPC GetOrder.
    """
    def get(self, request, order_id):
        stub = get_order_stub()
        grpc_request = customer_order_pb2.GetOrderRequest(order_id=order_id)

        try:
            grpc_response = stub.GetOrder(grpc_request)
            return Response(
                {
                    "order": proto_to_dict(grpc_response.order),
                },
                status=status.HTTP_200_OK,
            )
        except grpc.RpcError as e:
            raise GrpcClientError(e)


class CustomerOrderCancelView(APIView):
    """
    POST /api/v1/orders/<order_id>/cancel/ -> Cancel order via gRPC CancelOrder.
    """
    def post(self, request, order_id):
        serializer = CancelOrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        stub = get_order_stub()
        grpc_request = customer_order_pb2.CancelOrderRequest(
            order_id=order_id,
            actor_id=data["actor_id"],
            actor_type=customer_order_pb2.ACTOR_TYPE_CUSTOMER,
            reason=data.get("reason", ""),
        )

        try:
            grpc_response = stub.CancelOrder(grpc_request)
            return Response(
                {
                    "message": grpc_response.message,
                    "order": proto_to_dict(grpc_response.order),
                },
                status=status.HTTP_200_OK,
            )
        except grpc.RpcError as e:
            raise GrpcClientError(e)

