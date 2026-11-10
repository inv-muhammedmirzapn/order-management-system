import math
from typing import List, Dict, Any, Optional, Tuple
from django.db import transaction
from django.core.paginator import Paginator

from .models import Order, OrderItem, OrderActivity, OrderStatusChoices, ActorTypeChoices
from .exceptions import OrderNotFoundError, InvalidStateTransitionError, OrderValidationError

VALID_TRANSITIONS = {
    OrderStatusChoices.CREATED: {
        OrderStatusChoices.ASSIGNED,
        OrderStatusChoices.PROCESSING,
        OrderStatusChoices.CANCELLED,
    },
    OrderStatusChoices.ASSIGNED: {
        OrderStatusChoices.ASSIGNED,  # Reassignment
        OrderStatusChoices.PROCESSING,
        OrderStatusChoices.CANCELLED,
    },
    OrderStatusChoices.PROCESSING: {
        OrderStatusChoices.COMPLETED,
        OrderStatusChoices.CANCELLED,
    },
    OrderStatusChoices.COMPLETED: set(),  # Terminal state
    OrderStatusChoices.CANCELLED: set(),  # Terminal state
}


class AgentOrderDomainService:
    """Core domain service for Agent Order Management operations."""

    @staticmethod
    def get_order_by_id(order_id: str) -> Order:
        """Fetch order with preloaded relations, or raise OrderNotFoundError."""
        try:
            return (
                Order.objects.prefetch_related('items', 'activities')
                .get(id=order_id)
            )
        except (Order.DoesNotExist, ValueError):
            raise OrderNotFoundError(f"Order with ID '{order_id}' was not found.")

    @classmethod
    @transaction.atomic
    def create_order(
        cls,
        order_id: Optional[str],
        customer_id: str,
        customer_name: str,
        customer_email: str,
        shipping_address: str,
        items: List[Dict[str, Any]],
        notes: str = "",
    ) -> Order:
        """Create order in AgentOrderService DB (synced from CustomerOrderService)."""
        create_kwargs = {
            "customer_id": customer_id.strip(),
            "customer_name": customer_name.strip(),
            "customer_email": customer_email.strip(),
            "shipping_address": shipping_address.strip(),
            "status": OrderStatusChoices.CREATED,
            "notes": notes.strip() if notes else "",
        }
        if order_id and order_id.strip():
            create_kwargs["id"] = order_id.strip()

        order = Order.objects.create(**create_kwargs)

        total_amount = Decimal("0.00")
        for item_data in items:
            item_id = str(item_data.get("item_id", "")).strip()
            name = str(item_data.get("name", "")).strip()
            quantity = int(item_data.get("quantity", 1))
            unit_price = Decimal(str(item_data.get("unit_price", "0.00")))
            subtotal = Decimal(str(quantity)) * unit_price

            OrderItem.objects.create(
                order=order,
                item_id=item_id,
                name=name,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
            )
            total_amount += subtotal

        order.total_amount = total_amount
        order.save(update_fields=['total_amount'])

        OrderActivity.objects.create(
            order=order,
            action="ORDER_CREATED",
            actor_id=customer_id.strip(),
            actor_type=ActorTypeChoices.CUSTOMER,
            from_status="",
            to_status=OrderStatusChoices.CREATED,
            notes=f"Order created via CustomerOrderService gRPC sync. Total: ${total_amount:.2f}",
        )
        return cls.get_order_by_id(str(order.id))

    @classmethod
    def list_orders(
        cls,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Order], int, int]:
        """List orders with filtering and pagination."""
        qs = Order.objects.prefetch_related('items', 'activities').all()

        if status and status.strip():
            qs = qs.filter(status=status.strip().upper())
        if customer_id and customer_id.strip():
            qs = qs.filter(customer_id=customer_id.strip())
        if agent_id and agent_id.strip():
            qs = qs.filter(assigned_agent_id=agent_id.strip())

        total_count = qs.count()
        page_size = max(1, min(page_size, 100))
        page = max(1, page)
        total_pages = max(1, math.ceil(total_count / page_size)) if total_count > 0 else 1

        paginator = Paginator(qs, page_size)
        try:
            page_obj = paginator.page(page)
            orders = list(page_obj.object_list)
        except Exception:
            orders = []

        return orders, total_count, total_pages

    @classmethod
    @transaction.atomic
    def assign_order(
        cls,
        order_id: str,
        agent_id: str,
        agent_name: str,
        actor_id: str,
        notes: str = "",
    ) -> Order:
        """Assign or reassign an order to an agent."""
        order = cls.get_order_by_id(order_id)

        if order.status in (OrderStatusChoices.COMPLETED, OrderStatusChoices.CANCELLED):
            raise InvalidStateTransitionError(
                f"Cannot assign an order in terminal state '{order.status}'."
            )

        if not agent_id or not agent_id.strip():
            raise OrderValidationError("Agent ID is required for assignment.")

        prev_status = order.status
        prev_agent = f"{order.assigned_agent_name} ({order.assigned_agent_id})" if order.assigned_agent_id else "None"

        order.assigned_agent_id = agent_id.strip()
        order.assigned_agent_name = agent_name.strip() if agent_name else agent_id.strip()

        new_status = prev_status
        if order.status == OrderStatusChoices.CREATED:
            new_status = OrderStatusChoices.ASSIGNED
            order.status = new_status

        order.save()

        log_notes = f"Assigned to {order.assigned_agent_name} (ID: {order.assigned_agent_id}). Previous: {prev_agent}."
        if notes and notes.strip():
            log_notes += f" Note: {notes.strip()}"

        OrderActivity.objects.create(
            order=order,
            action="ORDER_ASSIGNED",
            actor_id=actor_id.strip() if actor_id else agent_id.strip(),
            actor_type=ActorTypeChoices.AGENT,
            from_status=prev_status,
            to_status=new_status,
            notes=log_notes,
        )

        return cls.get_order_by_id(order_id)

    @classmethod
    @transaction.atomic
    def start_order_processing(
        cls,
        order_id: str,
        agent_id: str = "",
        notes: str = "",
    ) -> Order:
        """Start processing an order. Order must not be completed or cancelled."""
        order = cls.get_order_by_id(order_id)

        if order.status in (OrderStatusChoices.COMPLETED, OrderStatusChoices.CANCELLED):
            raise InvalidStateTransitionError(
                f"Cannot start processing an order in terminal state '{order.status}'."
            )
        if order.status == OrderStatusChoices.PROCESSING:
            return order

        prev_status = order.status
        order.status = OrderStatusChoices.PROCESSING

        if agent_id and agent_id.strip() and not order.assigned_agent_id:
            order.assigned_agent_id = agent_id.strip()

        order.save()

        log_notes = f"Processing started by {agent_id or order.assigned_agent_id or 'agent'}."
        if notes and notes.strip():
            log_notes += f" Note: {notes.strip()}"

        OrderActivity.objects.create(
            order=order,
            action="PROCESSING_STARTED",
            actor_id=agent_id.strip() if agent_id else (order.assigned_agent_id or "agent"),
            actor_type=ActorTypeChoices.AGENT,
            from_status=prev_status,
            to_status=OrderStatusChoices.PROCESSING,
            notes=log_notes,
        )

        return cls.get_order_by_id(order_id)

    @classmethod
    @transaction.atomic
    def update_order_status(
        cls,
        order_id: str,
        new_status: str,
        actor_id: str,
        actor_type: str = ActorTypeChoices.AGENT,
        notes: str = "",
    ) -> Order:
        """Transition order to a new status with validation against state machine rules."""
        order = cls.get_order_by_id(order_id)
        current_status = order.status
        target_status = new_status.strip().upper()

        if target_status == current_status:
            return order

        allowed = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid status transition from '{current_status}' to '{target_status}'. "
                f"Allowed transitions: {list(allowed) if allowed else 'None (terminal state)'}."
            )

        order.status = target_status
        order.save(update_fields=['status', 'updated_at'])

        log_notes = f"Status updated from '{current_status}' to '{target_status}'."
        if notes and notes.strip():
            log_notes += f" Reason/Notes: {notes.strip()}"

        OrderActivity.objects.create(
            order=order,
            action="STATUS_UPDATED",
            actor_id=actor_id.strip() if actor_id else "unknown",
            actor_type=actor_type,
            from_status=current_status,
            to_status=target_status,
            notes=log_notes,
        )

        return cls.get_order_by_id(order_id)

    @classmethod
    @transaction.atomic
    def complete_order(
        cls,
        order_id: str,
        agent_id: str = "",
        notes: str = "",
    ) -> Order:
        """Complete an order."""
        order = cls.get_order_by_id(order_id)

        if order.status == OrderStatusChoices.COMPLETED:
            raise InvalidStateTransitionError(f"Order '{order_id}' is already completed.")
        if order.status == OrderStatusChoices.CANCELLED:
            raise InvalidStateTransitionError(
                f"Cannot complete order '{order_id}' because it has been CANCELLED."
            )

        prev_status = order.status
        order.status = OrderStatusChoices.COMPLETED
        order.save(update_fields=['status', 'updated_at'])

        log_notes = f"Order successfully completed."
        if notes and notes.strip():
            log_notes += f" Notes: {notes.strip()}"

        OrderActivity.objects.create(
            order=order,
            action="ORDER_COMPLETED",
            actor_id=agent_id.strip() if agent_id else (order.assigned_agent_id or "agent"),
            actor_type=ActorTypeChoices.AGENT,
            from_status=prev_status,
            to_status=OrderStatusChoices.COMPLETED,
            notes=log_notes,
        )

        return cls.get_order_by_id(order_id)

    @classmethod
    @transaction.atomic
    def add_order_activity(
        cls,
        order_id: str,
        action: str,
        actor_id: str,
        actor_type: str = ActorTypeChoices.AGENT,
        notes: str = "",
    ) -> Tuple[OrderActivity, Order]:
        """Add a custom activity or history entry for an order."""
        order = cls.get_order_by_id(order_id)

        if not action or not action.strip():
            raise OrderValidationError("Action name is required.")

        activity = OrderActivity.objects.create(
            order=order,
            action=action.strip().upper(),
            actor_id=actor_id.strip() if actor_id else "unknown",
            actor_type=actor_type,
            from_status=order.status,
            to_status=order.status,
            notes=notes.strip() if notes else "",
        )

        return activity, cls.get_order_by_id(order_id)

    @classmethod
    def get_order_activities(cls, order_id: str) -> List[OrderActivity]:
        """Fetch all activities / timeline events for an order."""
        order = cls.get_order_by_id(order_id)
        return list(order.activities.all())

