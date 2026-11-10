import grpc
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from generated import agent_order_pb2
from .grpc_client import (
    get_order_stub,
    proto_to_dict,
    GrpcClientError,
    STATUS_STR_TO_PROTO,
)
from .serializers import (
    AssignOrderSerializer,
    StartProcessingSerializer,
    UpdateStatusSerializer,
    CompleteOrderSerializer,
)


class OrderListView(APIView):
    """
    GET /api/v1/agent/orders/
    Query parameters: status, customer_id, agent_id, page, page_size
    """
    def get(self, request):
        status_param = request.query_params.get('status', '').upper()
        customer_id = request.query_params.get('customer_id', '')
        agent_id = request.query_params.get('agent_id', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        status_enum = STATUS_STR_TO_PROTO.get(status_param, agent_order_pb2.ORDER_STATUS_UNSPECIFIED)

        stub = get_order_stub()
        grpc_request = agent_order_pb2.ListOrdersRequest(
            status_filter=status_enum,
            customer_id_filter=customer_id,
            agent_id_filter=agent_id,
            page=page,
            page_size=page_size,
        )

        try:
            grpc_response = stub.ListOrders(grpc_request)
            return Response(
                {
                    "orders": [proto_to_dict(o) for o in grpc_response.orders],
                    "total_count": grpc_response.total_count,
                    "page": grpc_response.page,
                    "total_pages": grpc_response.total_pages,
                },
                status=status.HTTP_200_OK,
            )
        except grpc.RpcError as e:
            raise GrpcClientError(e)


class OrderDetailView(APIView):
    """
    GET /api/v1/agent/orders/<order_id>/
    """
    def get(self, request, order_id):
        stub = get_order_stub()
        grpc_request = agent_order_pb2.GetOrderRequest(order_id=order_id)

        try:
            grpc_response = stub.GetOrder(grpc_request)
            return Response(
                {"order": proto_to_dict(grpc_response.order)},
                status=status.HTTP_200_OK,
            )
        except grpc.RpcError as e:
            raise GrpcClientError(e)


class AssignOrderView(APIView):
    """
    POST /api/v1/agent/orders/<order_id>/assign/
    """
    def post(self, request, order_id):
        serializer = AssignOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        stub = get_order_stub()
        grpc_request = agent_order_pb2.AssignOrderRequest(
            order_id=order_id,
            agent_id=data["agent_id"],
            agent_name=data.get("agent_name", ""),
            actor_id=data.get("actor_id", data["agent_id"]),
            notes=data.get("notes", ""),
        )

        try:
            grpc_response = stub.AssignOrder(grpc_request)
            return Response(
                {
                    "message": grpc_response.message,
                    "order": proto_to_dict(grpc_response.order),
                },
                status=status.HTTP_200_OK,
            )
        except grpc.RpcError as e:
            raise GrpcClientError(e)


class StartProcessingView(APIView):
    """
    POST /api/v1/agent/orders/<order_id>/start-processing/
    """
    def post(self, request, order_id):
        serializer = StartProcessingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        stub = get_order_stub()
        grpc_request = agent_order_pb2.StartOrderProcessingRequest(
            order_id=order_id,
            agent_id=data.get("agent_id", ""),
            notes=data.get("notes", ""),
        )

        try:
            grpc_response = stub.StartOrderProcessing(grpc_request)
            return Response(
                {
                    "message": grpc_response.message,
                    "order": proto_to_dict(grpc_response.order),
                },
                status=status.HTTP_200_OK,
            )
        except grpc.RpcError as e:
            raise GrpcClientError(e)


class UpdateStatusView(APIView):
    """
    POST /api/v1/agent/orders/<order_id>/update-status/
    """
    def post(self, request, order_id):
        serializer = UpdateStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_status_enum = STATUS_STR_TO_PROTO[data["new_status"]]

        stub = get_order_stub()
        grpc_request = agent_order_pb2.UpdateOrderStatusRequest(
            order_id=order_id,
            new_status=new_status_enum,
            actor_id=data["actor_id"],
            actor_type=agent_order_pb2.ACTOR_TYPE_AGENT,
            notes=data.get("notes", ""),
        )

        try:
            grpc_response = stub.UpdateOrderStatus(grpc_request)
            return Response(
                {
                    "message": grpc_response.message,
                    "order": proto_to_dict(grpc_response.order),
                },
                status=status.HTTP_200_OK,
            )
        except grpc.RpcError as e:
            raise GrpcClientError(e)


class CompleteOrderView(APIView):
    """
    POST /api/v1/agent/orders/<order_id>/complete/
    """
    def post(self, request, order_id):
        serializer = CompleteOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        stub = get_order_stub()
        grpc_request = agent_order_pb2.CompleteOrderRequest(
            order_id=order_id,
            agent_id=data.get("agent_id", ""),
            notes=data.get("notes", ""),
        )

        try:
            grpc_response = stub.CompleteOrder(grpc_request)
            return Response(
                {
                    "message": grpc_response.message,
                    "order": proto_to_dict(grpc_response.order),
                },
                status=status.HTTP_200_OK,
            )
        except grpc.RpcError as e:
            raise GrpcClientError(e)


class OrderActivitiesView(APIView):
    """
    GET /api/v1/agent/orders/<order_id>/activities/
    """
    def get(self, request, order_id):
        stub = get_order_stub()
        grpc_request = agent_order_pb2.GetOrderActivitiesRequest(order_id=order_id)

        try:
            grpc_response = stub.GetOrderActivities(grpc_request)
            return Response(
                {
                    "activities": [proto_to_dict(a) for a in grpc_response.activities],
                },
                status=status.HTTP_200_OK,
            )
        except grpc.RpcError as e:
            raise GrpcClientError(e)

