import functools
import logging
import grpc
from django.db import connection, close_old_connections

from generated import customer_order_pb2, customer_order_pb2_grpc, agent_order_pb2
from .models import OrderStatusChoices, ActorTypeChoices
from .exceptions import OrderNotFoundError, InvalidStateTransitionError, OrderValidationError
from .services import CustomerOrderDomainService
from .agent_client import notify_agent_order_created, notify_agent_order_status_updated
from .serializers import (
    order_to_proto,
    STATUS_PROTO_TO_MODEL,
    ACTOR_PROTO_TO_MODEL,
)

logger = logging.getLogger(__name__)


def handle_grpc_exceptions(func):
    """
    Decorator for gRPC service methods to handle exceptions,
    set gRPC status codes, and manage Django database connections.
    """
    @functools.wraps(func)
    def wrapper(self, request, context):
        if not connection.in_atomic_block:
            close_old_connections()
        try:
            return func(self, request, context)
        except OrderNotFoundError as e:
            logger.warning(f"OrderNotFoundError in {func.__name__}: {e}")
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except InvalidStateTransitionError as e:
            logger.warning(f"InvalidStateTransitionError in {func.__name__}: {e}")
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except OrderValidationError as e:
            logger.warning(f"OrderValidationError in {func.__name__}: {e}")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Internal server error: {str(e)}")
        finally:
            if not connection.in_atomic_block:
                close_old_connections()
    return wrapper


class CustomerOrderGrpcServicer(customer_order_pb2_grpc.CustomerOrderServiceServicer):
    """
    gRPC Servicer implementing CustomerOrderService RPC endpoints.
    """

    @handle_grpc_exceptions
    def CreateOrder(self, request, context):
        items_data = [
            {
                "item_id": item.item_id,
                "name": item.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
            for item in request.items
        ]
        order = CustomerOrderDomainService.create_order(
            customer_id=request.customer_id,
            customer_name=request.customer_name,
            customer_email=request.customer_email,
            shipping_address=request.shipping_address,
            items=items_data,
            notes=request.notes,
        )

        # Notify AgentOrderService over gRPC (Decoupled microservice call)
        notify_agent_order_created(order)

        return customer_order_pb2.CreateOrderResponse(
            order=order_to_proto(order),
            message="Order created successfully.",
        )

    @handle_grpc_exceptions
    def GetOrder(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")
        order = CustomerOrderDomainService.get_order_by_id(request.order_id)
        return customer_order_pb2.GetOrderResponse(order=order_to_proto(order))

    @handle_grpc_exceptions
    def CancelOrder(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")

        actor_type = ACTOR_PROTO_TO_MODEL.get(request.actor_type, ActorTypeChoices.CUSTOMER)

        order = CustomerOrderDomainService.cancel_order(
            order_id=request.order_id,
            actor_id=request.actor_id,
            actor_type=actor_type,
            reason=request.reason,
        )

        # Notify AgentOrderService of cancellation over gRPC
        notify_agent_order_status_updated(
            order_id=order.id,
            new_status_enum=agent_order_pb2.ORDER_STATUS_CANCELLED,
            actor_id=request.actor_id,
            actor_type_enum=agent_order_pb2.ACTOR_TYPE_CUSTOMER,
            notes=request.reason,
        )

        return customer_order_pb2.CancelOrderResponse(
            order=order_to_proto(order),
            message="Order successfully cancelled.",
        )

    @handle_grpc_exceptions
    def UpdateOrderDetails(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")

        actor_type = ACTOR_PROTO_TO_MODEL.get(request.actor_type, ActorTypeChoices.CUSTOMER)
        items_data = None
        if request.items:
            items_data = [
                {
                    "item_id": item.item_id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                }
                for item in request.items
            ]

        order = CustomerOrderDomainService.update_order_details(
            order_id=request.order_id,
            actor_id=request.actor_id,
            actor_type=actor_type,
            shipping_address=request.shipping_address if request.shipping_address else None,
            notes=request.notes if request.notes else None,
            items=items_data,
        )
        return customer_order_pb2.UpdateOrderDetailsResponse(
            order=order_to_proto(order),
            message="Order details updated successfully.",
        )

    @handle_grpc_exceptions
    def SyncOrderStatus(self, request, context):
        """Called by AgentOrderService via gRPC when an agent changes status."""
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")

        status_model = STATUS_PROTO_TO_MODEL.get(request.new_status, OrderStatusChoices.PROCESSING)
        order = CustomerOrderDomainService.sync_status_from_agent(
            order_id=request.order_id,
            new_status=status_model,
            assigned_agent_id=request.assigned_agent_id if request.assigned_agent_id else None,
            assigned_agent_name=request.assigned_agent_name if request.assigned_agent_name else None,
            notes=request.notes,
        )
        return customer_order_pb2.SyncOrderStatusResponse(
            order=order_to_proto(order),
            message="Order status synced successfully.",
        )
