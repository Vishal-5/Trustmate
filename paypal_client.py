"""
TRUSTMATE - PayPal Integration Module (Person B)
Handles order creation and capture for PayPal Sandbox.
- Enforces fixed demo rate for INR to USD conversion (PayPal Sandbox requires USD).
- Supports PayPal MCP server (JSON-RPC) when available.
- Supports PayPal Sandbox REST API (/v2/checkout/orders).
- Provides high-fidelity Sandbox Simulator for local offline demoing.
"""

import os
import uuid
import httpx
from typing import Dict, Any, Optional

# Fixed demo conversion rate constant: 1 USD = ~83.33 INR (or 0.012 USD per INR)
USD_PER_INR_RATE = 0.012

def inr_to_usd(price_inr: float) -> float:
    """Converts price in INR to USD rounded to 2 decimal places."""
    return round(price_inr * USD_PER_INR_RATE, 2)

class PayPalClient:
    def __init__(self):
        self.client_id = os.getenv("PAYPAL_CLIENT_ID", "")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "")
        self.paypal_mcp_url = os.getenv("PAYPAL_MCP_URL", "")
        self.mode = os.getenv("PAYPAL_MODE", "sandbox") # "sandbox" or "simulator"

    def is_configured_live_sandbox(self) -> bool:
        return bool(self.client_id and self.client_secret and self.client_id != "your_paypal_client_id_here")

    async def _get_access_token(self) -> Optional[str]:
        """Fetches OAuth 2.0 access token from PayPal Sandbox REST API."""
        if not self.is_configured_live_sandbox():
            return None
        url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
        headers = {"Accept": "application/json", "Accept-Language": "en_US"}
        data = {"grant_type": "client_credentials"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, auth=(self.client_id, self.client_secret), data=data, headers=headers)
                if res.status_code == 200:
                    return res.json().get("access_token")
        except Exception as e:
            print(f"[PayPal] Failed to get OAuth token: {e}")
        return None

    async def create_order(
        self,
        item_title: str,
        price_inr: float,
        seller_name: str,
        return_url: str = "http://localhost:8000/checkout/success",
        cancel_url: str = "http://localhost:8000/checkout/cancel"
    ) -> Dict[str, Any]:
        """
        Creates a PayPal checkout order in USD with converted price.
        Returns order ID, approve_url, and amount breakdown.
        """
        amount_usd = inr_to_usd(price_inr)

        # 1. Check if PayPal MCP Server is running
        if self.paypal_mcp_url:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "create_order",
                            "arguments": {
                                "amount": str(amount_usd),
                                "currency": "USD",
                                "description": f"{item_title} from {seller_name}"
                            }
                        }
                    }
                    res = await client.post(self.paypal_mcp_url, json=payload)
                    if res.status_code == 200:
                        data = res.json().get("result", {}).get("data", {})
                        if data and "id" in data:
                            return {
                                "order_id": data["id"],
                                "approve_url": data.get("approve_url", f"https://www.sandbox.paypal.com/checkoutnow?token={data['id']}"),
                                "amount_inr": price_inr,
                                "amount_usd": amount_usd,
                                "conversion_rate": f"1 USD = {1/USD_PER_INR_RATE:.2f} INR",
                                "status": "CREATED",
                                "source": "paypal_mcp"
                            }
            except Exception as e:
                print(f"[PayPal MCP] Call failed, falling back: {e}")

        # 2. Check if PayPal Sandbox REST API keys are present
        if self.is_configured_live_sandbox():
            token = await self._get_access_token()
            if token:
                url = "https://api-m.sandbox.paypal.com/v2/checkout/orders"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                }
                order_payload = {
                    "intent": "CAPTURE",
                    "purchase_units": [
                        {
                            "description": f"{item_title} ({seller_name})",
                            "amount": {
                                "currency_code": "USD",
                                "value": f"{amount_usd:.2f}"
                            }
                        }
                    ],
                    "application_context": {
                        "return_url": return_url,
                        "cancel_url": cancel_url,
                        "brand_name": "TRUSTMATE Safe Checkout",
                        "user_action": "PAY_NOW"
                    }
                }
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        res = await client.post(url, headers=headers, json=order_payload)
                        if res.status_code in (200, 201):
                            data = res.json()
                            order_id = data["id"]
                            approve_url = None
                            for link in data.get("links", []):
                                if link.get("rel") == "approve":
                                    approve_url = link.get("href")
                            return {
                                "order_id": order_id,
                                "approve_url": approve_url or f"https://www.sandbox.paypal.com/checkoutnow?token={order_id}",
                                "amount_inr": price_inr,
                                "amount_usd": amount_usd,
                                "conversion_rate": f"1 USD = {1/USD_PER_INR_RATE:.2f} INR",
                                "status": "CREATED",
                                "source": "paypal_sandbox_api"
                            }
                except Exception as e:
                    print(f"[PayPal Sandbox] Direct API error: {e}")

        # 3. High-fidelity Sandbox Simulator for local offline testing
        sim_order_id = f"PAYID-{uuid.uuid4().hex[:12].upper()}"
        return {
            "order_id": sim_order_id,
            "approve_url": f"/checkout/simulator?order_id={sim_order_id}&amount_usd={amount_usd}&amount_inr={price_inr}&seller={seller_name}&title={item_title}",
            "amount_inr": price_inr,
            "amount_usd": amount_usd,
            "conversion_rate": f"1 USD = {1/USD_PER_INR_RATE:.2f} INR",
            "status": "CREATED",
            "source": "sandbox_simulator",
            "note": "Running in PayPal Sandbox Simulation mode. Configure PAYPAL_CLIENT_ID & SECRET in .env for live PayPal Sandbox accounts."
        }

    async def capture_order(self, order_id: str) -> Dict[str, Any]:
        """
        Captures authorized PayPal payment.
        """
        # 1. MCP check
        if self.paypal_mcp_url:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    payload = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "capture_payment", "arguments": {"order_id": order_id}}
                    }
                    res = await client.post(self.paypal_mcp_url, json=payload)
                    if res.status_code == 200:
                        return {"order_id": order_id, "status": "COMPLETED", "capture_id": f"CAP-{order_id}", "source": "paypal_mcp"}
            except Exception as e:
                print(f"[PayPal MCP capture error]: {e}")

        # 2. REST API check
        if self.is_configured_live_sandbox():
            token = await self._get_access_token()
            if token:
                url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        res = await client.post(url, headers=headers)
                        if res.status_code in (200, 201):
                            data = res.json()
                            return {
                                "order_id": order_id,
                                "status": data.get("status", "COMPLETED"),
                                "capture_id": data.get("purchase_units", [{}])[0].get("payments", {}).get("captures", [{}])[0].get("id", f"CAP-{order_id}"),
                                "source": "paypal_sandbox_api"
                            }
                except Exception as e:
                    print(f"[PayPal capture REST error]: {e}")

        # 3. Simulator capture
        return {
            "order_id": order_id,
            "status": "COMPLETED",
            "capture_id": f"CAPTURE-{uuid.uuid4().hex[:10].upper()}",
            "source": "sandbox_simulator"
        }

paypal_client = PayPalClient()

