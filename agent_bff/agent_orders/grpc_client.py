import logging
import grpc
from django.conf import settings
from google.protobuf.json_format import MessageToDict
from rest_framework import status
from rest_framework.exceptions import APIException

from generated import agent_order_pb2, agent_order_pb2_grpc

logger = logging.getLogger(__name__)

STATUS_STR_TO_PROTO = {
    'CREATED': agent_order_pb2.ORDER_STATUS_CREATED,
    'ASSIGNED': agent_order_pb2.ORDER_STATUS_ASSIGNED,
    'PROCESSING': agent_order_pb2.ORDER_STATUS_PROCESSING,
    'COMPLETED': agent_order_pb2.ORDER_STATUS_COMPLETED,
    'CANCELLED': agent_order_pb2.ORDER_STATUS_CANCELLED,
}


class GrpcClientError(APIException):
    """Translates gRPC RpcError into clean DRF HTTP response."""
    def __init__(self, rpc_error: grpc.RpcError):
        code = rpc_error.code()
        details = rpc_error.details() or "An error occurred in Agent Order Microservice"
        
        status_map = {
            grpc.StatusCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
            grpc.StatusCode.INVALID_ARGUMENT: status.HTTP_400_BAD_REQUEST,
            grpc.StatusCode.FAILED_PRECONDITION: status.HTTP_409_CONFLICT,
            grpc.StatusCode.ALREADY_EXISTS: status.HTTP_409_CONFLICT,
            grpc.StatusCode.PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
            grpc.StatusCode.UNAUTHENTICATED: status.HTTP_401_UNAUTHORIZED,
            grpc.StatusCode.UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
        }
        
        self.status_code = status_map.get(code, status.HTTP_502_BAD_GATEWAY)
        self.detail = {
            "error": details,
            "grpc_code": code.name if code else "UNKNOWN",
        }
        super().__init__(self.detail)


def get_order_stub() -> agent_order_pb2_grpc.AgentOrderServiceStub:
    """Creates a gRPC channel and returns an AgentOrderServiceStub."""
    channel = grpc.insecure_channel(settings.AGENT_ORDER_GRPC_HOST)
    return agent_order_pb2_grpc.AgentOrderServiceStub(channel)


def proto_to_dict(proto_message) -> dict:
    """Converts a protobuf message to a standard Python dictionary."""
    return MessageToDict(proto_message, preserving_proto_field_name=True)

