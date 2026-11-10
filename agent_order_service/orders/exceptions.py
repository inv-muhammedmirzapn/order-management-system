class OrderServiceException(Exception):
    """Base exception for Order Service."""
    pass


class OrderNotFoundError(OrderServiceException):
    """Raised when an order does not exist."""
    pass


class InvalidStateTransitionError(OrderServiceException):
    """Raised when an order transition is not allowed by business rules."""
    pass


class OrderValidationError(OrderServiceException):
    """Raised when validation of input parameters fails."""
    pass

