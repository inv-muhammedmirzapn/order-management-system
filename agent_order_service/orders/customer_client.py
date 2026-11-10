import logging
import grpc
from django.conf import settings
from generated import customer_order_pb2, customer_order_pb2_grpc

logger = logging.getLogger(__name__)


def get_customer_order_stub() -> customer_order_pb2_grpc.CustomerOrderServiceStub:
    channel = grpc.insecure_channel(settings.CUSTOMER_ORDER_GRPC_HOST)
    return customer_order_pb2_grpc.CustomerOrderServiceStub(channel)


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

