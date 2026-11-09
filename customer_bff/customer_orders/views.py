import grpc
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from generated import order_pb2
from .grpc_client import get_order_stub, proto_to_dict, GrpcClientError
from .serializers import CreateOrderRequestSerializer, CancelOrderRequestSerializer


class CustomerOrderListCreateView(APIView):
    """
    POST /api/v1/orders/ -> Create a new order via gRPC CreateOrder.
    """
    def post(self, request):
        serializer = CreateOrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        stub = get_order_stub()
        grpc_items = [
            order_pb2.OrderItemInput(
                item_id=item["item_id"],
                name=item["name"],
                quantity=item["quantity"],
                unit_price=float(item["unit_price"]),
            )
            for item in data["items"]
        ]

        grpc_request = order_pb2.CreateOrderRequest(
            customer_id=data["customer_id"],
            customer_name=data["customer_name"],
            customer_email=data["customer_email"],
            shipping_address=data["shipping_address"],
            items=grpc_items,
            notes=data.get("notes", ""),
        )

        try:
            grpc_response = stub.CreateOrder(grpc_request)
            return Response(
                {
                    "message": grpc_response.message,
                    "order": proto_to_dict(grpc_response.order),
                },
                status=status.HTTP_201_CREATED,
            )
        except grpc.RpcError as e:
            raise GrpcClientError(e)


class CustomerOrderDetailView(APIView):
    """
    GET /api/v1/orders/<order_id>/ -> Fetch order details via gRPC GetOrder.
    """
    def get(self, request, order_id):
        stub = get_order_stub()
        grpc_request = order_pb2.GetOrderRequest(order_id=order_id)

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
        grpc_request = order_pb2.CancelOrderRequest(
            order_id=order_id,
            actor_id=data["actor_id"],
            actor_type=order_pb2.ACTOR_TYPE_CUSTOMER,
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

