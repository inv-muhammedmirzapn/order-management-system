from google.protobuf.timestamp_pb2 import Timestamp
from generated import agent_order_pb2, customer_order_pb2
from .models import Order, OrderItem, OrderActivity, OrderStatusChoices, ActorTypeChoices

# Map internal model status to customer_order_pb2.OrderStatus enum
MODEL_TO_CUSTOMER_PROTO_STATUS = {
    OrderStatusChoices.CREATED: customer_order_pb2.ORDER_STATUS_CREATED,
    OrderStatusChoices.ASSIGNED: customer_order_pb2.ORDER_STATUS_ASSIGNED,
    OrderStatusChoices.PROCESSING: customer_order_pb2.ORDER_STATUS_PROCESSING,
    OrderStatusChoices.COMPLETED: customer_order_pb2.ORDER_STATUS_COMPLETED,
    OrderStatusChoices.CANCELLED: customer_order_pb2.ORDER_STATUS_CANCELLED,
}

STATUS_MODEL_TO_PROTO = {
    OrderStatusChoices.CREATED: agent_order_pb2.ORDER_STATUS_CREATED,
    OrderStatusChoices.ASSIGNED: agent_order_pb2.ORDER_STATUS_ASSIGNED,
    OrderStatusChoices.PROCESSING: agent_order_pb2.ORDER_STATUS_PROCESSING,
    OrderStatusChoices.COMPLETED: agent_order_pb2.ORDER_STATUS_COMPLETED,
    OrderStatusChoices.CANCELLED: agent_order_pb2.ORDER_STATUS_CANCELLED,
}

STATUS_PROTO_TO_MODEL = {
    agent_order_pb2.ORDER_STATUS_CREATED: OrderStatusChoices.CREATED,
    agent_order_pb2.ORDER_STATUS_ASSIGNED: OrderStatusChoices.ASSIGNED,
    agent_order_pb2.ORDER_STATUS_PROCESSING: OrderStatusChoices.PROCESSING,
    agent_order_pb2.ORDER_STATUS_COMPLETED: OrderStatusChoices.COMPLETED,
    agent_order_pb2.ORDER_STATUS_CANCELLED: OrderStatusChoices.CANCELLED,
}

ACTOR_MODEL_TO_PROTO = {
    ActorTypeChoices.CUSTOMER: agent_order_pb2.ACTOR_TYPE_CUSTOMER,
    ActorTypeChoices.AGENT: agent_order_pb2.ACTOR_TYPE_AGENT,
    ActorTypeChoices.SYSTEM: agent_order_pb2.ACTOR_TYPE_SYSTEM,
}

ACTOR_PROTO_TO_MODEL = {
    agent_order_pb2.ACTOR_TYPE_CUSTOMER: ActorTypeChoices.CUSTOMER,
    agent_order_pb2.ACTOR_TYPE_AGENT: ActorTypeChoices.AGENT,
    agent_order_pb2.ACTOR_TYPE_SYSTEM: ActorTypeChoices.SYSTEM,
}


def datetime_to_timestamp(dt) -> Timestamp:
    """Convert Python datetime to Protobuf Timestamp."""
    ts = Timestamp()
    if dt:
        ts.FromDatetime(dt)
    return ts


def order_item_to_proto(item: OrderItem) -> agent_order_pb2.OrderItem:
    """Serialize OrderItem model to protobuf message."""
    return agent_order_pb2.OrderItem(
        item_id=str(item.item_id),
        name=str(item.name),
        quantity=int(item.quantity),
        unit_price=float(item.unit_price),
        subtotal=float(item.subtotal),
    )


def order_activity_to_proto(activity: OrderActivity) -> agent_order_pb2.OrderActivity:
    """Serialize OrderActivity model to protobuf message."""
    proto_activity = agent_order_pb2.OrderActivity(
        id=str(activity.id),
        order_id=str(activity.order_id),
        action=str(activity.action),
        actor_id=str(activity.actor_id),
        actor_type=ACTOR_MODEL_TO_PROTO.get(activity.actor_type, agent_order_pb2.ACTOR_TYPE_UNSPECIFIED),
        from_status=str(activity.from_status or ""),
        to_status=str(activity.to_status or ""),
        notes=str(activity.notes or ""),
    )
    if activity.timestamp:
        proto_activity.timestamp.CopyFrom(datetime_to_timestamp(activity.timestamp))
    return proto_activity


def order_to_proto(order: Order) -> agent_order_pb2.Order:
    """Serialize Order model to protobuf message including items and activities."""
    proto_order = agent_order_pb2.Order(
        id=str(order.id),
        customer_id=str(order.customer_id),
        customer_name=str(order.customer_name),
        customer_email=str(order.customer_email),
        shipping_address=str(order.shipping_address),
        status=STATUS_MODEL_TO_PROTO.get(order.status, agent_order_pb2.ORDER_STATUS_UNSPECIFIED),
        assigned_agent_id=str(order.assigned_agent_id or ""),
        assigned_agent_name=str(order.assigned_agent_name or ""),
        total_amount=float(order.total_amount),
        notes=str(order.notes or ""),
    )

    if order.created_at:
        proto_order.created_at.CopyFrom(datetime_to_timestamp(order.created_at))
    if order.updated_at:
        proto_order.updated_at.CopyFrom(datetime_to_timestamp(order.updated_at))

    # Add items
    proto_order.items.extend([order_item_to_proto(item) for item in order.items.all()])

    # Add activities
    proto_order.activities.extend([order_activity_to_proto(act) for act in order.activities.all()])

    return proto_order

