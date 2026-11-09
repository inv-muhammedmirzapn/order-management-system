class OrderServiceError(Exception):
    """Base exception for order service."""
    pass


class OrderNotFoundError(OrderServiceError):
    """Raised when an order is not found."""
    pass


class InvalidStateTransitionError(OrderServiceError):
    """Raised when an invalid state transition is attempted."""
    pass


class OrderValidationError(OrderServiceError):
    """Raised when order input data fails validation."""
    pass

