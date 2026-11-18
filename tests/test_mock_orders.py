import pytest

from app.data.mock_orders import MOCK_ORDERS, lookup_order_status


def test_lookup_existing_order():
    result = lookup_order_status("ORD1001")
    assert result is not None
    assert result["order_id"] == "ORD1001"
    assert result["status"] == "Shipped"
    assert result["estimated_delivery"] == "2026-11-20"
    assert result["tracking_number"] == "TRK12345"


def test_lookup_order_without_tracking():
    result = lookup_order_status("ORD1002")
    assert result is not None
    assert result["status"] == "Processing"
    assert result["tracking_number"] is None


def test_lookup_delivered_order():
    result = lookup_order_status("ORD1003")
    assert result is not None
    assert result["status"] == "Delivered"
    assert result["estimated_delivery"] == "2026-11-17"


def test_lookup_unknown_order():
    result = lookup_order_status("ORD9999")
    assert result is None


def test_lookup_empty_order_id():
    with pytest.raises(ValueError, match="non-empty"):
        lookup_order_status("")


def test_lookup_whitespace_order_id():
    with pytest.raises(ValueError, match="non-empty"):
        lookup_order_status("   ")


def test_lookup_invalid_type():
    with pytest.raises(ValueError, match="non-empty"):
        lookup_order_status(123)  # type: ignore[arg-type]


def test_mock_orders_has_three_orders():
    assert len(MOCK_ORDERS) == 3
    assert set(MOCK_ORDERS.keys()) == {"ORD1001", "ORD1002", "ORD1003"}


def test_returned_order_is_copy_or_shared():
    result = lookup_order_status("ORD1001")
    assert result is not None
    assert result["order_id"] == "ORD1001"
