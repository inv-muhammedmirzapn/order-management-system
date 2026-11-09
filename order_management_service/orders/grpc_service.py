import functools
import logging
import grpc
from django.db import connection, close_old_connections

from generated import order_pb2, order_pb2_grpc
from .models import OrderStatusChoices, ActorTypeChoices
from .exceptions import OrderNotFoundError, InvalidStateTransitionError, OrderValidationError
from .services import OrderDomainService
from .serializers import (
    order_to_proto,
    order_activity_to_proto,
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


class OrderGrpcServicer(order_pb2_grpc.OrderServiceServicer):
    """
    gRPC Servicer implementing all OrderService RPC endpoints.
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
        order = OrderDomainService.create_order(
            customer_id=request.customer_id,
            customer_name=request.customer_name,
            customer_email=request.customer_email,
            shipping_address=request.shipping_address,
            items=items_data,
            notes=request.notes,
        )
        return order_pb2.CreateOrderResponse(
            order=order_to_proto(order),
            message="Order created successfully.",
        )

    @handle_grpc_exceptions
    def GetOrder(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")
        order = OrderDomainService.get_order_by_id(request.order_id)
        return order_pb2.GetOrderResponse(order=order_to_proto(order))

    @handle_grpc_exceptions
    def ListOrders(self, request, context):
        status_model = STATUS_PROTO_TO_MODEL.get(request.status_filter, None)
        orders, total_count, total_pages = OrderDomainService.list_orders(
            status=status_model,
            customer_id=request.customer_id_filter if request.customer_id_filter else None,
            agent_id=request.agent_id_filter if request.agent_id_filter else None,
            page=request.page if request.page > 0 else 1,
            page_size=request.page_size if request.page_size > 0 else 20,
        )
        return order_pb2.ListOrdersResponse(
            orders=[order_to_proto(o) for o in orders],
            total_count=total_count,
            page=request.page if request.page > 0 else 1,
            total_pages=total_pages,
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

        order = OrderDomainService.update_order_details(
            order_id=request.order_id,
            actor_id=request.actor_id,
            actor_type=actor_type,
            shipping_address=request.shipping_address if request.shipping_address else None,
            notes=request.notes if request.notes else None,
            items=items_data,
        )
        return order_pb2.UpdateOrderDetailsResponse(
            order=order_to_proto(order),
            message="Order details updated successfully.",
        )

    @handle_grpc_exceptions
    def AssignOrder(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")
        if not request.agent_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "agent_id must be provided.")

        order = OrderDomainService.assign_order(
            order_id=request.order_id,
            agent_id=request.agent_id,
            agent_name=request.agent_name,
            actor_id=request.actor_id or request.agent_id,
            notes=request.notes,
        )
        return order_pb2.AssignOrderResponse(
            order=order_to_proto(order),
            message=f"Order successfully assigned to {request.agent_name or request.agent_id}.",
        )

    @handle_grpc_exceptions
    def StartOrderProcessing(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")

        order = OrderDomainService.start_order_processing(
            order_id=request.order_id,
            agent_id=request.agent_id,
            notes=request.notes,
        )
        return order_pb2.StartOrderProcessingResponse(
            order=order_to_proto(order),
            message="Order processing started successfully.",
        )

    @handle_grpc_exceptions
    def UpdateOrderStatus(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")
        if request.new_status == order_pb2.ORDER_STATUS_UNSPECIFIED:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Valid new_status must be provided.")

        new_status_str = STATUS_PROTO_TO_MODEL.get(request.new_status)
        if not new_status_str:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Unknown status: {request.new_status}")

        actor_type = ACTOR_PROTO_TO_MODEL.get(request.actor_type, ActorTypeChoices.AGENT)

        order = OrderDomainService.update_order_status(
            order_id=request.order_id,
            new_status=new_status_str,
            actor_id=request.actor_id,
            actor_type=actor_type,
            notes=request.notes,
        )
        return order_pb2.UpdateOrderStatusResponse(
            order=order_to_proto(order),
            message=f"Order status updated to {new_status_str}.",
        )

    @handle_grpc_exceptions
    def AddOrderActivity(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")
        if not request.action:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "action must be provided.")

        actor_type = ACTOR_PROTO_TO_MODEL.get(request.actor_type, ActorTypeChoices.AGENT)

        activity, order = OrderDomainService.add_order_activity(
            order_id=request.order_id,
            action=request.action,
            actor_id=request.actor_id,
            actor_type=actor_type,
            notes=request.notes,
        )
        return order_pb2.AddOrderActivityResponse(
            activity=order_activity_to_proto(activity),
            order=order_to_proto(order),
            message="Order activity added successfully.",
        )

    @handle_grpc_exceptions
    def CancelOrder(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")

        actor_type = ACTOR_PROTO_TO_MODEL.get(request.actor_type, ActorTypeChoices.CUSTOMER)

        order = OrderDomainService.cancel_order(
            order_id=request.order_id,
            actor_id=request.actor_id,
            actor_type=actor_type,
            reason=request.reason,
        )
        return order_pb2.CancelOrderResponse(
            order=order_to_proto(order),
            message="Order successfully cancelled.",
        )

    @handle_grpc_exceptions
    def CompleteOrder(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")

        order = OrderDomainService.complete_order(
            order_id=request.order_id,
            agent_id=request.agent_id,
            notes=request.notes,
        )
        return order_pb2.CompleteOrderResponse(
            order=order_to_proto(order),
            message="Order completed successfully.",
        )

    @handle_grpc_exceptions
    def GetOrderActivities(self, request, context):
        if not request.order_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "order_id must be provided.")

        activities = OrderDomainService.get_order_activities(request.order_id)
        return order_pb2.GetOrderActivitiesResponse(
            activities=[order_activity_to_proto(a) for a in activities]
        )

