import logging
import atexit
from typing import Optional
import grpc
from django.conf import settings
from generated import customer_order_pb2, customer_order_pb2_grpc

logger = logging.getLogger(__name__)

_channel: Optional[grpc.Channel] = None
_stub: Optional[customer_order_pb2_grpc.CustomerOrderServiceStub] = None


def get_channel() -> grpc.Channel:
    """Returns a singleton gRPC channel to the Customer Order Microservice."""
    global _channel
    if _channel is None:
        _channel = grpc.insecure_channel(settings.CUSTOMER_ORDER_GRPC_HOST)
    return _channel


def get_customer_order_stub() -> customer_order_pb2_grpc.CustomerOrderServiceStub:
    """Returns a singleton CustomerOrderServiceStub reusing the active channel."""
    global _stub
    if _stub is None:
        _stub = customer_order_pb2_grpc.CustomerOrderServiceStub(get_channel())
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


def sync_status_to_customer_service(
    order_id: str,
    new_status_enum: int,
    assigned_agent_id: str = "",
    assigned_agent_name: str = "",
    notes: str = "",
):
    """Notify CustomerOrderService that an agent has updated an order's status."""
    try:
        stub = get_customer_order_stub()
        request = customer_order_pb2.SyncOrderStatusRequest(
            order_id=str(order_id),
            new_status=new_status_enum,
            assigned_agent_id=assigned_agent_id or "",
            assigned_agent_name=assigned_agent_name or "",
            notes=notes or "",
        )
        response = stub.SyncOrderStatus(request)
        logger.info(f"Successfully synced status for order {order_id} to CustomerOrderService: {response.message}")
        return response
    except grpc.RpcError as e:
        logger.error(f"Failed to sync status for order {order_id} to CustomerOrderService: {e.code()} - {e.details()}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error notifying CustomerOrderService for order {order_id}: {e}")
        return None

