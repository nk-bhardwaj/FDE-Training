"""Customer-support order lookup tool definitions and registry."""

from collections.abc import Callable
from typing import Any

from app.data.mock_orders import lookup_order_status

TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "lookup_order_status": {
        "name": "lookup_order_status",
        "description": "Look up the current status and delivery details of a customer order.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": 'The order ID to look up (e.g. "ORD1001").',
                },
            },
            "required": ["order_id"],
        },
    },
}

TOOL_REGISTRY: dict[str, Callable[..., Any]] = {
    "lookup_order_status": lookup_order_status,
}


def get_tool(name: str) -> Callable[..., Any]:
    """Retrieve an allowed tool by name.

    Args:
        name: The tool name to look up.

    Returns:
        The registered callable associated with the tool name.

    Raises:
        ValueError: If the tool name is not registered.
    """
    if name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {name}")
    return TOOL_REGISTRY[name]
