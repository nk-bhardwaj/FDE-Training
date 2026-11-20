"""Sample documents for semantic search in e-commerce order and delivery support."""

from typing import Any

SAMPLE_DOCUMENTS: list[dict[str, Any]] = [
    {
        "content": "Where is my order ORD1001? I need the tracking information and current status.",
        "metadata": {"category": "order_tracking", "source": "web"},
    },
    {
        "content": "My package was supposed to arrive yesterday but the status still shows transit. Can you check the delivery timeline?",
        "metadata": {"category": "delivery_delays", "source": "email"},
    },
    {
        "content": "I want to return a defective item purchased last week. What is the return process and refund timeline?",
        "metadata": {"category": "returns_refunds", "source": "web"},
    },
    {
        "content": "Cancel my recent order ORD1005 before it ships. I changed my mind and need the cancellation confirmed.",
        "metadata": {"category": "cancellations", "source": "mobile_app"},
    },
    {
        "content": "Payment failed at checkout. My card should have sufficient funds. Why was the transaction declined?",
        "metadata": {"category": "payment_failures", "source": "web"},
    },
    {
        "content": "Received a damaged product in the shipment. The box was crushed and the item inside is broken. How do I get a replacement?",
        "metadata": {"category": "damaged_products", "source": "email"},
    },
    {
        "content": "Forgot my password and cannot log into my account. Send me a password reset link immediately.",
        "metadata": {"category": "account_login_issues", "source": "web"},
    },
    {
        "content": "Why am I paying $9.99 shipping on a $50 order? The shipping charges seem excessive for the delivery speed.",
        "metadata": {"category": "shipping_charges", "source": "phone"},
    },
    {
        "content": "I ordered a different size of the same product. Can I exchange it for the correct size without paying again?",
        "metadata": {"category": "exchanges", "source": "web"},
    },
    {
        "content": "Nobody is responding to my support tickets about a missing package. I need urgent help tracking ORD1002.",
        "metadata": {"category": "customer_support", "source": "phone"},
    },
    {
        "content": "Order ORD1003 shows delivered but I never received the package. Neighbour might have taken it. What are next steps?",
        "metadata": {"category": "order_tracking", "source": "email"},
    },
    {
        "content": "Delivery was delayed due to weather conditions. Updated estimated arrival is 3 days later than promised.",
        "metadata": {"category": "delivery_delays", "source": "web"},
    },
    {
        "content": "Returned an unworn jacket last month but refund hasn't appeared in my account yet. Status check needed.",
        "metadata": {"category": "returns_refunds", "source": "mobile_app"},
    },
    {
        "content": "Subscription renewal charged twice this month. Need refund for the duplicate payment.",
        "metadata": {"category": "payment_failures", "source": "email"},
    },
    {
        "content": "Item arrived with a tear and missing parts. Quality control issue. Want full refund or replacement.",
        "metadata": {"category": "damaged_products", "source": "phone"},
    },
    {
        "content": "Account locked after multiple failed login attempts. Unlock my account so I can place a new order.",
        "metadata": {"category": "account_login_issues", "source": "web"},
    },
    {
        "content": "Free shipping threshold is $75 but my order total is $68. Will you apply a promo code to waive the $5.99 fee?",
        "metadata": {"category": "shipping_charges", "source": "web"},
    },
    {
        "content": "Exchanged a defective blender for a newer model. Return label was emailed but never arrived. Follow-up needed.",
        "metadata": {"category": "exchanges", "source": "email"},
    },
    {
        "content": "Chat agent gave me wrong tracking info. Order status still shows processing after 5 days. Escalate please.",
        "metadata": {"category": "customer_support", "source": "phone"},
    },
    {
        "content": "Where is my order ORD1007? The tracking number TRK99999 isn't scanning at any facility.",
        "metadata": {"category": "order_tracking", "source": "mobile_app"},
    },
    {
        "content": "Package arrived 2 weeks late with no prior notification. Dissatisfied customer requesting compensation.",
        "metadata": {"category": "delivery_delays", "source": "email"},
    },
    {
        "content": "Initiated a return for refund on damaged headphones. Return window is closing soon. Need urgent assistance.",
        "metadata": {"category": "returns_refunds", "source": "web"},
    },
    {
        "content": "Order cancellation confirmed but still receiving shipping notifications. Stop all further communications.",
        "metadata": {"category": "cancellations", "source": "mobile_app"},
    },
    {
        "content": "Payment keeps failing with insufficient funds error. Tried three different cards. What's going on?",
        "metadata": {"category": "payment_failures", "source": "phone"},
    },
    {
        "content": "Missing item in my delivery. Order ORD1001 arrived but the box only had 3 of 5 items. Where are the others?",
        "metadata": {"category": "damaged_products", "source": "email"},
    },
    {
        "content": "Forgot username for login. Need help recovering account credentials to access order history.",
        "metadata": {"category": "account_login_issues", "source": "web"},
    },
    {
        "content": "Shipping charge was applied even though I selected free shipping at checkout. Billing discrepancy.",
        "metadata": {"category": "shipping_charges", "source": "phone"},
    },
    {
        "content": "Want to exchange winter coat for different colour. Same price point. Process time and restocking fee?",
        "metadata": {"category": "exchanges", "source": "web"},
    },
    {
        "content": "Support agent disconnected mid-conversation while I was waiting for order ORD1004 update. Need follow-up.",
        "metadata": {"category": "customer_support", "source": "phone"},
    },
    {
        "content": "Placed order ORD1006 by mistake during checkout. Cancel immediately before shipment to avoid charge.",
        "metadata": {"category": "cancellations", "source": "web"},
    },
]
