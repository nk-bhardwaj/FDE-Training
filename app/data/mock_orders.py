"""Mock order data for LLM tool-calling demonstration."""

from typing import Any

MOCK_ORDERS: dict[str, dict[str, Any]] = {
    "ORD1001": {
        "order_id": "ORD1001",
        "status": "Shipped",
        "estimated_delivery": "2026-11-20",
        "tracking_number": "TRK12345",
    },
    "ORD1002": {
        "order_id": "ORD1002",
        "status": "Processing",
        "estimated_delivery": "2026-11-22",
        "tracking_number": None,
    },
    "ORD1003": {
        "order_id": "ORD1003",
        "status": "Delivered",
        "estimated_delivery": "2026-11-17",
        "tracking_number": "TRK67890",
    },
}


def lookup_order_status(order_id: str) -> dict[str, Any] | None:
    """Look up an order by its ID using mock data.

    Args:
        order_id: The order ID to look up (e.g. "ORD1001").

    Returns:
        The order details as a dict when found, otherwise None.

    Raises:
        ValueError: If the order ID is empty or not a valid string.

    Note:
        This is mock data for demonstration purposes and is not real data.
    """
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("order_id must be a non-empty string")
    return MOCK_ORDERS.get(order_id)
