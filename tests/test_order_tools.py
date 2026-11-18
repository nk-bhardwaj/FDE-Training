import pytest

from app.data.mock_orders import lookup_order_status as real_lookup
from app.tools.order_tools import TOOL_DEFINITIONS, TOOL_REGISTRY, get_tool


def test_tool_definition_structure():
    assert "lookup_order_status" in TOOL_DEFINITIONS
    tool = TOOL_DEFINITIONS["lookup_order_status"]

    assert tool["name"] == "lookup_order_status"
    assert (
        tool["description"]
        == "Look up the current status and delivery details of a customer order."
    )

    params = tool["parameters"]
    assert params["type"] == "object"
    assert "order_id" in params["properties"]
    assert params["properties"]["order_id"]["type"] == "string"
    assert params["required"] == ["order_id"]


def test_registered_tool_lookup():
    tool_fn = get_tool("lookup_order_status")
    assert callable(tool_fn)
    assert tool_fn is real_lookup


def test_unknown_tool_rejection():
    with pytest.raises(ValueError, match="Unknown tool"):
        get_tool("delete_everything")


def test_registry_maps_to_existing_lookup_function():
    assert TOOL_REGISTRY["lookup_order_status"] is real_lookup

    result = TOOL_REGISTRY["lookup_order_status"]("ORD1001")
    assert result is not None
    assert result["status"] == "Shipped"


def test_registry_and_definitions_stay_in_sync():
    assert set(TOOL_REGISTRY.keys()) == set(TOOL_DEFINITIONS.keys())
