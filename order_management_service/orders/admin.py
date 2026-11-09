from django.contrib import admin
from .models import Order, OrderItem, OrderActivity


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('subtotal',)


class OrderActivityInline(admin.TabularInline):
    model = OrderActivity
    extra = 0
    readonly_fields = ('timestamp', 'action', 'actor_id', 'actor_type', 'from_status', 'to_status', 'notes')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'status', 'total_amount', 'assigned_agent_name', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'customer_name', 'customer_email', 'assigned_agent_name')
    inlines = [OrderItemInline, OrderActivityInline]
    readonly_fields = ('id', 'total_amount', 'created_at', 'updated_at')


@admin.register(OrderActivity)
class OrderActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'action', 'actor_id', 'actor_type', 'from_status', 'to_status', 'timestamp')
    list_filter = ('action', 'actor_type', 'timestamp')
    search_fields = ('order__id', 'actor_id', 'notes')
    readonly_fields = ('id', 'timestamp')
