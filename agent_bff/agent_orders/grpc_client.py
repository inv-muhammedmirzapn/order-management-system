import logging
import atexit
from typing import Optional
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


_channel: Optional[grpc.Channel] = None
_stub: Optional[agent_order_pb2_grpc.AgentOrderServiceStub] = None


def get_channel() -> grpc.Channel:
    """Returns a singleton gRPC channel to the Agent Order Microservice."""
    global _channel
    if _channel is None:
        _channel = grpc.insecure_channel(settings.AGENT_ORDER_GRPC_HOST)
    return _channel


def get_order_stub() -> agent_order_pb2_grpc.AgentOrderServiceStub:
    """Returns a singleton AgentOrderServiceStub reusing the active channel."""
    global _stub
    if _stub is None:
        _stub = agent_order_pb2_grpc.AgentOrderServiceStub(get_channel())
    return _stub


def close_channel():
    """Closes the gRPC channel and resets the client."""
    global _channel, _stub
    if _channel is not None:
        try:
            _channel.close()
        except Exception:
            pass
        _channel = None
        _stub = None


atexit.register(close_channel)


def proto_to_dict(proto_message) -> dict:
    """Converts a protobuf message to a standard Python dictionary."""
    return MessageToDict(proto_message, preserving_proto_field_name=True)

