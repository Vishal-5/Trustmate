"""
TRUSTMATE - Customer-Facing Web Application & Agent Server (Person B)
Serves the user interface, manages the agent loop, and interfaces with PayPal and TRUSTMATE MCP servers.
"""

import os
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from agent import agent, parse_user_request
from paypal_client import paypal_client, inr_to_usd, USD_PER_INR_RATE
from storage import log_order_created, log_order_captured, get_dashboard_data

app = FastAPI(title="TRUSTMATE Customer Portal", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REQUEST MODELS ---

class SearchRequest(BaseModel):
    query: str

class ExplainRequest(BaseModel):
    seller: str
    url: Optional[str] = None

class CreateOrderRequest(BaseModel):
    item_title: str
    seller_name: str
    price_inr: float
    trust_score: Optional[float] = None
    trust_label: str = "Unrated"
    risk_confirmed: bool = False

class CaptureOrderRequest(BaseModel):
    order_id: str

# --- API ROUTES ---

@app.get("/api/status")
async def get_system_status():
    return {
        "trust_mcp_url": agent.mcp_url,
        "paypal_mode": "Live Sandbox" if paypal_client.is_configured_live_sandbox() else "Sandbox Simulator",
        "currency_rate": f"1 USD = {1/USD_PER_INR_RATE:.2f} INR (Fixed demo rate)"
    }

@app.post("/api/search")
async def api_search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    result = await agent.execute_search(req.query)
    return result

@app.post("/api/explain")
async def api_explain(req: ExplainRequest):
    explanation = await agent.get_seller_explanation(req.seller, req.url)
    return {"seller": req.seller, "summary": explanation}

@app.post("/api/order/create")
async def api_create_order(req: CreateOrderRequest):
    # Rule: If seller trust score is under 2.5, enforce explicit second confirmation
    if req.trust_score is not None and req.trust_score < 2.5 and not req.risk_confirmed:
        return JSONResponse(
            status_code=400,
            content={
                "error": "LOW_TRUST_CONFIRMATION_REQUIRED",
                "message": f"This seller scored {req.trust_score:.1f} (Risky). You must explicitly acknowledge the risk to proceed.",
                "trust_score": req.trust_score,
                "trust_label": req.trust_label
            }
        )

    order_info = await paypal_client.create_order(
        item_title=req.item_title,
        price_inr=req.price_inr,
        seller_name=req.seller_name
    )

    log_order_created(
        order_id=order_info["order_id"],
        item_title=req.item_title,
        seller_name=req.seller_name,
        amount_inr=req.price_inr,
        amount_usd=order_info["amount_usd"],
        trust_score=req.trust_score,
        trust_label=req.trust_label,
        risk_confirmed=req.risk_confirmed
    )

    return order_info

@app.post("/api/order/capture")
async def api_capture_order(req: CaptureOrderRequest):
    res = await paypal_client.capture_order(req.order_id)
    if res.get("status") == "COMPLETED":
        log_order_captured(req.order_id, res.get("capture_id", ""))
    return res

@app.get("/api/dashboard")
async def api_dashboard():
    return get_dashboard_data()

# --- SANDBOX SIMULATOR APPROVAL UI (For seamless local/offline testing) ---
@app.get("/checkout/simulator", response_class=HTMLResponse)
async def checkout_simulator_page(order_id: str, amount_usd: str, amount_inr: str, seller: str, title: str):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PayPal Sandbox Approval - TRUSTMATE</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 flex items-center justify-center min-h-screen p-4 font-sans">
        <div class="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-slate-200">
            <div class="flex items-center justify-between pb-4 border-b border-slate-100">
                <div class="flex items-center space-x-2">
                    <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center font-bold text-white text-lg">P</div>
                    <span class="text-xl font-bold text-slate-800">PayPal <span class="text-xs bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded">SANDBOX</span></span>
                </div>
                <span class="text-xs text-slate-400">Order: {order_id[:12]}...</span>
            </div>

            <div class="my-6 space-y-3">
                <div class="bg-slate-50 p-4 rounded-xl space-y-2 border border-slate-100">
                    <p class="text-xs text-slate-500 uppercase tracking-wider font-semibold">Payment Details</p>
                    <p class="text-sm font-semibold text-slate-800">{title}</p>
                    <p class="text-xs text-slate-500">Merchant: <span class="font-medium text-slate-700">{seller}</span></p>
                    <div class="pt-2 flex justify-between items-baseline border-t border-slate-200/60">
                        <span class="text-sm text-slate-600">Total USD:</span>
                        <span class="text-2xl font-bold text-slate-900">${amount_usd}</span>
                    </div>
                    <div class="flex justify-between items-baseline text-xs text-slate-400">
                        <span>Original Price:</span>
                        <span>₹{float(amount_inr):,.2f} INR (at 1 USD = {1/USD_PER_INR_RATE:.2f} INR)</span>
                    </div>
                </div>

                <div class="bg-emerald-50 border border-emerald-100 p-3 rounded-lg flex items-center space-x-2 text-xs text-emerald-800">
                    <svg class="w-4 h-4 text-emerald-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                    <span>TRUSTMATE Safe Checkout verified order.</span>
                </div>
            </div>

            <div class="space-y-3">
                <button onclick="approveOrder()" id="payBtn" class="w-full bg-[#0070BA] hover:bg-[#005ea6] text-white font-semibold py-3 px-4 rounded-xl shadow-md transition flex items-center justify-center space-x-2">
                    <span>Approve & Complete Payment</span>
                </button>
                <button onclick="window.close()" class="w-full text-center text-xs text-slate-500 hover:text-slate-700 py-1">
                    Cancel and return to TRUSTMATE
                </button>
            </div>
        </div>

        <script>
            async function approveOrder() {{
                const btn = document.getElementById('payBtn');
                btn.disabled = true;
                btn.innerHTML = '<span class="animate-spin mr-2">⏳</span> Authorizing on PayPal Sandbox...';
                
                try {{
                    const res = await fetch('/api/order/capture', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ order_id: '{order_id}' }})
                    }});
                    const data = await res.json();
                    
                    if (data.status === 'COMPLETED') {{
                        alert('🎉 Payment Captured Successfully in PayPal Sandbox! Capture ID: ' + data.capture_id);
                        if (window.opener) {{
                            window.opener.postMessage({{ type: 'PAYPAL_ORDER_CAPTURED', order_id: '{order_id}' }}, '*');
                            window.close();
                        }} else {{
                            window.location.href = '/?order_success={order_id}';
                        }}
                    }} else {{
                        alert('Payment Capture Failed: ' + JSON.stringify(data));
                        btn.disabled = false;
                        btn.innerText = 'Approve & Complete Payment';
                    }}
                }} catch (err) {{
                    alert('Error capturing payment: ' + err.message);
                    btn.disabled = false;
                    btn.innerText = 'Approve & Complete Payment';
                }}
            }}
        </script>
    </body>
    </html>
    """

# --- API ROOT ENDPOINT (UI is hosted in Next.js frontend on port 3000) ---
@app.get("/")
def api_root():
    return {
        "service": "TRUSTMATE API Gateway & Agent (Person B)",
        "status": "online",
        "frontend": "http://127.0.0.1:3000",
        "endpoints": {
            "search": "POST /api/search",
            "explain": "POST /api/explain",
            "order_create": "POST /api/order/create",
            "order_capture": "POST /api/order/capture",
            "dashboard": "GET /api/dashboard",
            "status": "GET /api/status"
        }
    }

if __name__ == "__main__":
    import uvicorn
    app_dir = os.path.dirname(os.path.abspath(__file__))
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, app_dir=app_dir)

