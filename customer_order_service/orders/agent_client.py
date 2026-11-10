import logging
import grpc
from django.conf import settings
from generated import agent_order_pb2, agent_order_pb2_grpc

logger = logging.getLogger(__name__)


def get_agent_order_stub() -> agent_order_pb2_grpc.AgentOrderServiceStub:
    channel = grpc.insecure_channel(settings.AGENT_ORDER_GRPC_HOST)
    return agent_order_pb2_grpc.AgentOrderServiceStub(channel)


def notify_agent_order_created(order):
    """Notify AgentOrderService that a new order has been created."""
    try:
        stub = get_agent_order_stub()
        items = [
            agent_order_pb2.OrderItemInput(
                item_id=item.item_id,
                name=item.name,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
            )
            for item in order.items.all()
        ]
        request = agent_order_pb2.CreateOrderRequest(
            id=str(order.id),
            customer_id=order.customer_id,
            customer_name=order.customer_name,
            customer_email=order.customer_email,
            shipping_address=order.shipping_address,
            items=items,
            notes=order.notes,
        )
        response = stub.CreateOrder(request)
        logger.info(f"Successfully synced order {order.id} to AgentOrderService: {response.message}")
        return response
    except grpc.RpcError as e:
        logger.error(f"Failed to sync created order {order.id} to AgentOrderService: {e.code()} - {e.details()}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error calling AgentOrderService for order {order.id}: {e}")
        return None


def notify_agent_order_status_updated(order_id: str, new_status_enum, actor_id: str, actor_type_enum, notes: str = ""):
    """Notify AgentOrderService of order status updates (e.g. cancellation)."""
    try:
        stub = get_agent_order_stub()
        request = agent_order_pb2.UpdateOrderStatusRequest(
            order_id=str(order_id),
            new_status=new_status_enum,
            actor_id=actor_id,
            actor_type=actor_type_enum,
            notes=notes,
        )
        response = stub.UpdateOrderStatus(request)
        logger.info(f"Successfully synced order status {order_id} to AgentOrderService: {response.message}")
        return response
    except grpc.RpcError as e:
        logger.error(f"Failed to sync status for order {order_id} to AgentOrderService: {e.code()} - {e.details()}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error notifying AgentOrderService for order {order_id}: {e}")
        return None

