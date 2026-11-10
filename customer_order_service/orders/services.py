from decimal import Decimal
from typing import List, Dict, Any, Optional
from django.db import transaction

from .models import Order, OrderItem, OrderActivity, OrderStatusChoices, ActorTypeChoices
from .exceptions import OrderNotFoundError, InvalidStateTransitionError, OrderValidationError


class CustomerOrderDomainService:
    """Core domain service for Customer Order operations."""

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
        customer_id: str,
        customer_name: str,
        customer_email: str,
        shipping_address: str,
        items: List[Dict[str, Any]],
        notes: str = "",
    ) -> Order:
        """Create a new order with items and log initial activity."""
        if not customer_id or not customer_id.strip():
            raise OrderValidationError("Customer ID is required.")
        if not customer_name or not customer_name.strip():
            raise OrderValidationError("Customer Name is required.")
        if not shipping_address or not shipping_address.strip():
            raise OrderValidationError("Shipping address is required.")
        if not items:
            raise OrderValidationError("Order must contain at least one item.")

        order = Order.objects.create(
            customer_id=customer_id.strip(),
            customer_name=customer_name.strip(),
            customer_email=customer_email.strip(),
            shipping_address=shipping_address.strip(),
            status=OrderStatusChoices.CREATED,
            notes=notes.strip() if notes else "",
        )

        total_amount = Decimal("0.00")
        for item_data in items:
            item_id = str(item_data.get("item_id", "")).strip()
            name = str(item_data.get("name", "")).strip()
            quantity = int(item_data.get("quantity", 1))
            unit_price = Decimal(str(item_data.get("unit_price", "0.00")))

            if not item_id or not name:
                raise OrderValidationError("Each item must have an item_id and name.")
            if quantity <= 0:
                raise OrderValidationError(f"Invalid quantity {quantity} for item '{name}'. Must be > 0.")
            if unit_price < Decimal("0.00"):
                raise OrderValidationError(f"Invalid unit price {unit_price} for item '{name}'.")

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
            notes=f"Order created with {len(items)} items. Total: ${total_amount:.2f}",
        )

        return cls.get_order_by_id(str(order.id))

    @classmethod
    @transaction.atomic
    def cancel_order(
        cls,
        order_id: str,
        actor_id: str,
        actor_type: str = ActorTypeChoices.CUSTOMER,
        reason: str = "",
    ) -> Order:
        """Cancel an order. Orders that are COMPLETED cannot be cancelled."""
        order = cls.get_order_by_id(order_id)

        if order.status == OrderStatusChoices.CANCELLED:
            raise InvalidStateTransitionError(f"Order '{order_id}' is already cancelled.")
        if order.status == OrderStatusChoices.COMPLETED:
            raise InvalidStateTransitionError(
                f"Cannot cancel order '{order_id}' because it has already been COMPLETED."
            )

        prev_status = order.status
        order.status = OrderStatusChoices.CANCELLED
        order.save(update_fields=['status', 'updated_at'])

        log_notes = f"Order cancelled. Reason: {reason.strip() if reason else 'No reason provided.'}"
        OrderActivity.objects.create(
            order=order,
            action="ORDER_CANCELLED",
            actor_id=actor_id.strip() if actor_id else "unknown",
            actor_type=actor_type,
            from_status=prev_status,
            to_status=OrderStatusChoices.CANCELLED,
            notes=log_notes,
        )

        return cls.get_order_by_id(order_id)

    @classmethod
    @transaction.atomic
    def update_order_details(
        cls,
        order_id: str,
        actor_id: str,
        actor_type: str = ActorTypeChoices.CUSTOMER,
        shipping_address: Optional[str] = None,
        notes: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
    ) -> Order:
        """Update order details (address, notes, or items)."""
        order = cls.get_order_by_id(order_id)

        if order.status in (OrderStatusChoices.COMPLETED, OrderStatusChoices.CANCELLED):
            raise InvalidStateTransitionError(
                f"Cannot update details of an order with status '{order.status}'."
            )

        changes = []
        if shipping_address is not None and shipping_address.strip() and shipping_address.strip() != order.shipping_address:
            order.shipping_address = shipping_address.strip()
            changes.append("shipping_address updated")

        if notes is not None and notes.strip() != order.notes:
            order.notes = notes.strip()
            changes.append("notes updated")

        if items is not None:
            if len(items) == 0:
                raise OrderValidationError("Order must have at least one item.")

            order.items.all().delete()
            total_amount = Decimal("0.00")
            for item_data in items:
                item_id = str(item_data.get("item_id", "")).strip()
                name = str(item_data.get("name", "")).strip()
                quantity = int(item_data.get("quantity", 1))
                unit_price = Decimal(str(item_data.get("unit_price", "0.00")))

                if not item_id or not name:
                    raise OrderValidationError("Each item must have an item_id and name.")
                if quantity <= 0:
                    raise OrderValidationError(f"Invalid quantity {quantity} for item '{name}'.")
                if unit_price < Decimal("0.00"):
                    raise OrderValidationError(f"Invalid unit price {unit_price} for item '{name}'.")

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
            changes.append(f"items updated (total: ${total_amount:.2f})")

        order.save()

        summary = ", ".join(changes) if changes else "No changes made."
        OrderActivity.objects.create(
            order=order,
            action="DETAILS_UPDATED",
            actor_id=actor_id.strip() if actor_id else "unknown",
            actor_type=actor_type,
            from_status=order.status,
            to_status=order.status,
            notes=summary,
        )

        return cls.get_order_by_id(order_id)

    @classmethod
    @transaction.atomic
    def sync_status_from_agent(
        cls,
        order_id: str,
        new_status: str,
        assigned_agent_id: Optional[str] = None,
        assigned_agent_name: Optional[str] = None,
        notes: str = "",
    ) -> Order:
        """Sync order status update initiated by AgentOrderService."""
        order = cls.get_order_by_id(order_id)
        prev_status = order.status
        order.status = new_status
        update_fields = ['status', 'updated_at']
        if assigned_agent_id is not None:
            order.assigned_agent_id = assigned_agent_id
            update_fields.append('assigned_agent_id')
        if assigned_agent_name is not None:
            order.assigned_agent_name = assigned_agent_name
            update_fields.append('assigned_agent_name')
        order.save(update_fields=update_fields)

        OrderActivity.objects.create(
            order=order,
            action=f"STATUS_SYNCED_{new_status}",
            actor_id=assigned_agent_id or "agent_service",
            actor_type=ActorTypeChoices.AGENT,
            from_status=prev_status,
            to_status=new_status,
            notes=notes or f"Status updated to {new_status} via AgentOrderService sync",
        )
        return cls.get_order_by_id(order_id)


