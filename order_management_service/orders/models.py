import uuid
from decimal import Decimal
from django.db import models


class OrderStatusChoices(models.TextChoices):
    CREATED = 'CREATED', 'Created'
    ASSIGNED = 'ASSIGNED', 'Assigned'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ActorTypeChoices(models.TextChoices):
    CUSTOMER = 'CUSTOMER', 'Customer'
    AGENT = 'AGENT', 'Agent'
    SYSTEM = 'SYSTEM', 'System'


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_id = models.CharField(max_length=64, db_index=True)
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    shipping_address = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=OrderStatusChoices.choices,
        default=OrderStatusChoices.CREATED,
        db_index=True,
    )
    assigned_agent_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
    )
    assigned_agent_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} ({self.customer_name}) - {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    item_id = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(str(self.quantity)) * Decimal(str(self.unit_price))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (x{self.quantity}) - ${self.subtotal}"


class OrderActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='activities',
    )
    action = models.CharField(max_length=64)
    actor_id = models.CharField(max_length=64)
    actor_type = models.CharField(
        max_length=32,
        choices=ActorTypeChoices.choices,
        default=ActorTypeChoices.SYSTEM,
    )
    from_status = models.CharField(max_length=32, blank=True, null=True)
    to_status = models.CharField(max_length=32, blank=True, null=True)
    notes = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.order.id}: {self.action} by {self.actor_type}:{self.actor_id}"
