"""
Tests for Person B (Agent, Contract Shapes, Mock MCP Server, Storage, Gating, PayPal flow)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mock.mock_mcp_server import (
    execute_rank_offers,
    execute_get_trust_score,
    execute_explain_score,
    build_trust_object
)
from agent import parse_user_request
from paypal_client import inr_to_usd, USD_PER_INR_RATE
from storage import (
    log_search,
    log_order_created,
    log_order_captured,
    get_dashboard_data
)

def test_query_parsing():
    q1, b1 = parse_user_request("laptop under 60000 for programming")
    assert "laptop" in q1.lower()
    assert b1 == 60000.0

    q2, b2 = parse_user_request("headphones under Rs 15,000")
    assert "headphones" in q2.lower()
    assert b2 == 15000.0

    q3, b3 = parse_user_request("mechanical keyboard 4k")
    assert "keyboard" in q3.lower()
    assert b3 == 4000.0

def test_currency_conversion():
    # 1 USD = ~83.33 INR (rate = 0.012)
    assert inr_to_usd(60000) == 720.0
    assert inr_to_usd(55000) == 660.0
    assert inr_to_usd(42000) == 504.0

def test_mock_mcp_contract_shapes():
    # Test rank_offers
    res = execute_rank_offers("laptop", 60000)
    assert "offers" in res
    assert "unverified_notes" in res
    offers = res["offers"]
    assert len(offers) == 4

    # Verify required mock seller types exist:
    # 1 cheap Risky seller (<2.5)
    # 1 Unrated seller (null score)
    # 2 Trusted sellers (>=4.0)
    risky_offers = [o for o in offers if o["trust"]["label"] == "Risky"]
    unrated_offers = [o for o in offers if o["trust"]["label"] == "Unrated"]
    trusted_offers = [o for o in offers if o["trust"]["label"] == "Trusted"]

    assert len(risky_offers) >= 1
    assert len(unrated_offers) >= 1
    assert len(trusted_offers) >= 2

    # Verify Risky seller is NEVER recommended
    assert risky_offers[0]["recommended"] is False
    assert risky_offers[0]["trust"]["score"] < 2.5
    assert risky_offers[0]["tradeoff_note"] is not None

    # Verify Top pick is Recommended
    assert offers[0]["recommended"] is True
    assert offers[0]["trust"]["score"] >= 4.0

def test_mock_mcp_direct_tools():
    data = execute_get_trust_score("TechWorld Prime")
    assert data["score"] >= 4.0
    assert data["label"] == "Trusted"
    assert len(data["factors"]) > 0

    res_exp = execute_explain_score("MegaElectronics Bargain")
    assert "summary" in res_exp
    assert "High risk" in res_exp["summary"]

    res_unrated = execute_get_trust_score("DevStore Direct")
    assert res_unrated["score"] is None
    assert res_unrated["label"] == "Unrated"

def test_gating_logic():
    # Rule: Sellers with score < 2.5 require explicit confirmation
    def check_can_proceed(score: float, risk_confirmed: bool) -> bool:
        if score is not None and score < 2.5 and not risk_confirmed:
            return False
        return True

    assert check_can_proceed(1.9, False) is False
    assert check_can_proceed(1.9, True) is True
    assert check_can_proceed(4.7, False) is True
    assert check_can_proceed(None, False) is True

def test_storage_and_dashboard():
    # Log a test search
    log_search("laptop for programming", 60000, [{"id": 1}], ["Note 1"])

    # Log an order creation & capture
    order_id = "TEST-ORDER-12345"
    log_order_created(
        order_id=order_id,
        item_title="Pro Laptop",
        seller_name="TechWorld Prime",
        amount_inr=55000,
        amount_usd=660.0,
        trust_score=4.7,
        trust_label="Trusted"
    )
    log_order_captured(order_id, "TEST-CAPTURE-999")

    # Verify dashboard returns persisted data
    data = get_dashboard_data()
    assert len(data["orders"]) >= 1
    captured_orders = [o for o in data["orders"] if o["order_id"] == order_id]
    assert len(captured_orders) == 1
    assert captured_orders[0]["status"] == "COMPLETED"
    assert captured_orders[0]["capture_id"] == "TEST-CAPTURE-999"
