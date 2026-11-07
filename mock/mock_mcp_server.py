"""
TRUSTMATE - Mock MCP Server (Person B testing stub)
Implements the exact frozen contract for TRUSTMATE MCP tools:
1. rank_offers({ query: string, budget_inr: number })
2. get_trust_score({ seller: string, url?: string })
3. explain_score({ seller: string, url?: string })

Supports both:
- MCP JSON-RPC 2.0 (POST /mcp or POST /)
- Direct HTTP REST (POST /tools/<tool_name>)
"""

from typing import Dict, Any, Optional, List
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="TRUSTMATE Mock MCP Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MOCK DATA MATCHING CONTRACT REQUIREMENTS ---
# Must include:
# 1 cheap Risky seller (<2.5)
# 1 Unrated seller (null score)
# 2 Trusted sellers (>=4.0)

MOCK_DATABASE = {
    "megaelectronics bargain": {
        "score": 1.9,
        "label": "Risky",
        "confidence": "high",
        "factors": [
            {
                "name": "Google Places",
                "status": "bad",
                "detail": "No registered physical store or verified Google business profile found."
            },
            {
                "name": "Customer Reviews",
                "status": "bad",
                "detail": "Average 1.8/5 on independent review boards. Multiple complaints regarding non-delivery."
            },
            {
                "name": "Domain Age & HTTPS",
                "status": "warn",
                "detail": "Domain registered only 18 days ago. HTTPS enabled via free certificate."
            },
            {
                "name": "Policy & Contact",
                "status": "bad",
                "detail": "No valid phone number or physical address on return policy page."
            },
            {
                "name": "Safe Browsing",
                "status": "ok",
                "detail": "No active malware or phishing signatures detected by Safe Browsing."
            }
        ],
        "summary": "High risk detected. Domain is under 3 weeks old with no physical business presence, missing return contact details, and multiple customer non-delivery complaints on independent forums."
    },
    "techworld prime": {
        "score": 4.7,
        "label": "Trusted",
        "confidence": "high",
        "factors": [
            {
                "name": "Google Places",
                "status": "ok",
                "detail": "Verified business in Bengaluru, 4.6/5 stars across 1,840 Google reviews."
            },
            {
                "name": "Customer Reviews",
                "status": "ok",
                "detail": "Consistently high ratings across 5 years with steady, authentic review volume."
            },
            {
                "name": "Domain Age & HTTPS",
                "status": "ok",
                "detail": "Domain active for 7 years. EV SSL certificate with strong encryption."
            },
            {
                "name": "Policy & Contact",
                "status": "ok",
                "detail": "Clear 14-day replacement policy, verified GSTIN, and direct phone support."
            },
            {
                "name": "Safe Browsing",
                "status": "ok",
                "detail": "Clean reputation on Google Safe Browsing."
            }
        ],
        "summary": "Highly trusted merchant. 7-year established domain with verified physical presence, over 1,800 authentic reviews, clear return policies, and verified business registration."
    },
    "omniretail hub": {
        "score": 4.3,
        "label": "Trusted",
        "confidence": "high",
        "factors": [
            {
                "name": "Google Places",
                "status": "ok",
                "detail": "Verified retail presence in Mumbai, 4.3/5 stars across 420 reviews."
            },
            {
                "name": "Customer Reviews",
                "status": "ok",
                "detail": "Positive sentiment regarding packaging and timely dispatch."
            },
            {
                "name": "Domain Age & HTTPS",
                "status": "ok",
                "detail": "Domain active for 3 years. Valid HTTPS."
            },
            {
                "name": "Policy & Contact",
                "status": "ok",
                "detail": "Transparent return policy with working email and support desk."
            },
            {
                "name": "Safe Browsing",
                "status": "ok",
                "detail": "Clean reputation on Safe Browsing."
            }
        ],
        "summary": "Established and verified seller. Active physical presence in Mumbai with solid multi-year reputation, HTTPS security, and responsive customer service."
    },
    "devstore direct": {
        "score": None,
        "label": "Unrated",
        "confidence": "low",
        "factors": [
            {
                "name": "Google Places",
                "status": "unverified",
                "detail": "Could not verify physical location or Places listing."
            },
            {
                "name": "Customer Reviews",
                "status": "unverified",
                "detail": "Insufficient external review volume to assess sentiment."
            },
            {
                "name": "Domain Age & HTTPS",
                "status": "ok",
                "detail": "Active HTTPS certificate. Domain registered 11 months ago."
            },
            {
                "name": "Policy & Contact",
                "status": "warn",
                "detail": "Contact form available, but physical address could not be verified."
            },
            {
                "name": "Safe Browsing",
                "status": "ok",
                "detail": "No malicious reports on Google Safe Browsing."
            }
        ],
        "summary": "Seller is currently Unrated. Insufficient verifiable historical data or public review records. Proceed with standard online caution."
    }
}

def find_seller_data(seller_query: str) -> Dict[str, Any]:
    key = seller_query.lower().strip()
    for s_name, data in MOCK_DATABASE.items():
        if s_name in key or key in s_name:
            return data
    # Default unrated if completely unknown
    return {
        "score": None,
        "label": "Unrated",
        "confidence": "low",
        "factors": [
            {"name": "Google Places", "status": "unverified", "detail": "No public business listing found."},
            {"name": "Customer Reviews", "status": "unverified", "detail": "Insufficient review data."},
            {"name": "Domain Age & HTTPS", "status": "unverified", "detail": "Domain signals could not be fetched."},
            {"name": "Policy & Contact", "status": "unverified", "detail": "Could not verify contact policy."},
            {"name": "Safe Browsing", "status": "ok", "detail": "No threats reported."}
        ],
        "summary": "Unrated merchant. Not enough public verifiable data exists to compute a trust rating."
    }

def build_trust_object(seller_name: str) -> Dict[str, Any]:
    data = find_seller_data(seller_name)
    return {
        "score": data["score"],
        "label": data["label"],
        "confidence": data["confidence"],
        "factors": data["factors"]
    }

# --- TOOL IMPLEMENTATIONS ---

def execute_get_trust_score(seller: str, url: Optional[str] = None) -> Dict[str, Any]:
    return build_trust_object(seller)

def execute_explain_score(seller: str, url: Optional[str] = None) -> Dict[str, str]:
    data = find_seller_data(seller)
    return {"summary": data["summary"]}

def execute_rank_offers(query: str, budget_inr: float) -> Dict[str, Any]:
    # Returns 4 distinct offers matching Person B requirements:
    # 1. Cheap Risky seller (e.g. ₹42,000 when budget is ~60k) - NEVER recommended
    # 2. Top Trusted seller (e.g. ₹55,000) - RECOMMENDED
    # 3. Alternative Trusted seller (e.g. ₹56,500)
    # 4. Unrated seller (e.g. ₹58,000)

    # Base pricing adjusted around the user's budget if reasonable, else standard laptop prices
    base_budget = budget_inr if budget_inr and budget_inr > 10000 else 60000

    risky_price = int(base_budget * 0.70)      # e.g., ₹42,000 (huge discount)
    trusted_1_price = int(base_budget * 0.91)  # e.g., ₹55,000
    trusted_2_price = int(base_budget * 0.94)  # e.g., ₹56,500
    unrated_price = int(base_budget * 0.96)    # e.g., ₹58,000

    price_diff = trusted_1_price - risky_price

    offers = [
        # Rank 1: Top Trusted merchant
        {
            "id": "offer-techworld-01",
            "title": f"{query.title()} - Pro Certified Edition",
            "price_inr": trusted_1_price,
            "url": "https://techworldprime.example.in/item/101",
            "seller": "TechWorld Prime",
            "trust": build_trust_object("TechWorld Prime"),
            "rank": 1,
            "recommended": True,
            "tradeoff_note": None
        },
        # Rank 2: Alternative Trusted merchant
        {
            "id": "offer-omni-02",
            "title": f"{query.title()} - Retail Authorized Pack",
            "price_inr": trusted_2_price,
            "url": "https://omniretail.example.in/product/992",
            "seller": "OmniRetail Hub",
            "trust": build_trust_object("OmniRetail Hub"),
            "rank": 2,
            "recommended": False,
            "tradeoff_note": None
        },
        # Rank 3: Unrated merchant
        {
            "id": "offer-devstore-03",
            "title": f"{query.title()} - Direct Import",
            "price_inr": unrated_price,
            "url": "https://devstore-direct.example.in/p/441",
            "seller": "DevStore Direct",
            "trust": build_trust_object("DevStore Direct"),
            "rank": 3,
            "recommended": False,
            "tradeoff_note": None
        },
        # Rank 4: Cheap Risky merchant (CHEAPEST, but score < 2.5 so gated and never recommended!)
        {
            "id": "offer-mega-04",
            "title": f"{query.title()} - Super Saver Deal",
            "price_inr": risky_price,
            "url": "https://megaelectronics-bargain.shop/deal",
            "seller": "MegaElectronics Bargain",
            "trust": build_trust_object("MegaElectronics Bargain"),
            "rank": 4,
            "recommended": False,
            "tradeoff_note": f"₹{price_diff:,} cheaper but scored 1.9: newly registered domain (18 days old), no physical location verified, and multiple non-delivery complaints."
        }
    ]

    return {
        "offers": offers,
        "unverified_notes": [
            "DevStore Direct: Physical address could not be verified in Google Places registry.",
            "MegaElectronics Bargain: Merchant contact number returned invalid format."
        ]
    }

# --- REST ENDPOINTS ---

class RankOffersRequest(BaseModel):
    query: str
    budget_inr: float

class SellerRequest(BaseModel):
    seller: str
    url: Optional[str] = None

@app.post("/tools/rank_offers")
async def api_rank_offers(req: RankOffersRequest):
    return execute_rank_offers(req.query, req.budget_inr)

@app.post("/tools/get_trust_score")
async def api_get_trust_score(req: SellerRequest):
    return execute_get_trust_score(req.seller, req.url)

@app.post("/tools/explain_score")
async def api_explain_score(req: SellerRequest):
    return execute_explain_score(req.seller, req.url)

# --- MCP JSON-RPC 2.0 PROTOCOL ENDPOINTS ---

@app.post("/")
@app.post("/mcp")
async def handle_mcp_rpc(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None})

    method = body.get("method")
    req_id = body.get("id")
    params = body.get("params", {})

    if method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "rank_offers",
                        "description": "Searches and ranks product offers trust-first based on seller authenticity",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "budget_inr": {"type": "number"}
                            },
                            "required": ["query", "budget_inr"]
                        }
                    },
                    {
                        "name": "get_trust_score",
                        "description": "Calculates and returns the trust score object for a seller",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "seller": {"type": "string"},
                                "url": {"type": "string"}
                            },
                            "required": ["seller"]
                        }
                    },
                    {
                        "name": "explain_score",
                        "description": "Generates a human-friendly concise explanation of a seller trust score",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "seller": {"type": "string"},
                                "url": {"type": "string"}
                            },
                            "required": ["seller"]
                        }
                    }
                ]
            }
        })

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "rank_offers":
            res = execute_rank_offers(args.get("query", "Laptop"), float(args.get("budget_inr", 60000)))
            return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": str(res)}], "data": res}})

        elif tool_name == "get_trust_score":
            res = execute_get_trust_score(args.get("seller", ""), args.get("url"))
            return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": str(res)}], "data": res}})

        elif tool_name == "explain_score":
            res = execute_explain_score(args.get("seller", ""), args.get("url"))
            return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": str(res)}], "data": res}})

        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
            })

    elif method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "trustmate-mock-mcp", "version": "1.0.0"}
            }
        })

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not supported: {method}"}
    })

@app.get("/health")
def health():
    return {"status": "ok", "server": "trustmate-mock-mcp", "contract": "v1-frozen"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)

