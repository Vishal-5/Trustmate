"""
TRUSTMATE - Agent Orchestrator (Person B)
Implements the core agent loop according to Person B specification:
1. Extract query & budget from user request.
2. Call TRUST_MCP_URL rank_offers.
   STRICT RULE: Person B NEVER re-ranks, re-scores, or hides offers.
3. Show offers in the order given by Person A's server.
4. When tapped, fetch explain_score.
5. Create PayPal order only after explicit customer approval.
6. Enforce second confirmation if trust.score < 2.5.
7. Treat "Unrated" (score: null) as Unrated, never bad.
"""

import os
import re
import json
import httpx
from typing import Dict, Any, Optional, Tuple, List
from storage import log_search

DEFAULT_MOCK_MCP_URL = "http://127.0.0.1:8001"

def parse_user_request(user_input: str) -> Tuple[str, float]:
    """
    Extracts search query and budget_inr from plain text customer input.
    Examples:
    - 'laptop under 60000 for programming' -> ('laptop for programming', 60000.0)
    - 'headphones under Rs 15,000' -> ('headphones', 15000.0)
    - 'ipad 80k' -> ('ipad', 80000.0)
    """
    text = user_input.strip()
    budget = 60000.0 # Default fallback budget

    # Match patterns like: under 60000, under rs 60,000, under ₹60,000, 60k
    k_match = re.search(r'(?:under\s+)?(?:rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*k\b', text, re.IGNORECASE)
    if k_match:
        budget = float(k_match.group(1)) * 1000
        # clean the budget phrase from the query
        clean_query = re.sub(r'\b(?:under\s+)?(?:rs\.?|₹)?\s*\d+(?:\.\d+)?\s*k\b', '', text, flags=re.IGNORECASE)
    else:
        num_match = re.search(r'(?:under|below|budget|within|max)\s*(?:of\s*)?(?:rs\.?|inr|₹)?\s*([\d,]+)', text, re.IGNORECASE)
        if num_match:
            raw_num = num_match.group(1).replace(',', '')
            try:
                budget = float(raw_num)
            except ValueError:
                budget = 60000.0
            clean_query = re.sub(r'(?:under|below|budget|within|max)\s*(?:of\s*)?(?:rs\.?|inr|₹)?\s*[\d,]+', '', text, flags=re.IGNORECASE)
        else:
            clean_query = text

    clean_query = re.sub(r'\s+', ' ', clean_query).strip()
    if not clean_query:
        clean_query = "Product"

    return clean_query, budget

class TrustmateAgent:
    def __init__(self):
        self.mcp_url = os.getenv("TRUST_MCP_URL", DEFAULT_MOCK_MCP_URL).rstrip("/")

    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Calls a tool on the TRUSTMATE MCP server via:
        1. JSON-RPC (POST /mcp or POST /)
        2. Fallback to direct HTTP REST (POST /tools/<tool_name>)
        """
        url = self.mcp_url
        timeout = 10.0

        # Attempt 1: Standard MCP JSON-RPC
        payload_rpc = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                res = await client.post(f"{url}/mcp", json=payload_rpc)
                if res.status_code == 200:
                    json_data = res.json()
                    if "result" in json_data:
                        result = json_data["result"]
                        # Extract data field if provided, else parse content text
                        if "data" in result:
                            return result["data"]
                        if "content" in result and len(result["content"]) > 0:
                            content_text = result["content"][0].get("text", "")
                            try:
                                return json.loads(content_text.replace("'", "\""))
                            except Exception:
                                pass
            except Exception:
                pass

            # Attempt 2: Direct REST route /tools/{tool_name}
            try:
                res = await client.post(f"{url}/tools/{tool_name}", json=arguments)
                if res.status_code == 200:
                    return res.json()
            except Exception as e:
                # If local mock server is not running on port 8001, fallback to in-process mock
                if "127.0.0.1" in url or "localhost" in url:
                    print(f"[Agent] Local MCP server offline at {url}, using in-process mock fallback...")
                    try:
                        from mock.mock_mcp_server import (
                            execute_rank_offers,
                            execute_get_trust_score,
                            execute_explain_score
                        )
                        if tool_name == "rank_offers":
                            return execute_rank_offers(arguments.get("query", ""), float(arguments.get("budget_inr", 60000)))
                        elif tool_name == "get_trust_score":
                            return execute_get_trust_score(arguments.get("seller", ""), arguments.get("url"))
                        elif tool_name == "explain_score":
                            return execute_explain_score(arguments.get("seller", ""), arguments.get("url"))
                    except Exception as inner_e:
                        print(f"[Agent] In-process fallback error: {inner_e}")
                print(f"[Agent MCP Error] Calling {tool_name} on {url} failed: {e}")
                raise e

    async def execute_search(self, user_prompt: str) -> Dict[str, Any]:
        """
        Agent Step 1-3:
        Parses user intent, executes rank_offers, logs search, and returns ranked results.
        CRITICAL RULE: Results are returned exactly in Person A's ranked order without any local re-ordering!
        """
        query, budget = parse_user_request(user_prompt)

        try:
            result = await self._call_mcp_tool("rank_offers", {
                "query": query,
                "budget_inr": budget
            })
        except Exception as e:
            # If server connection failed, inform the caller
            return {
                "success": False,
                "error": f"Failed to communicate with TRUSTMATE MCP server at {self.mcp_url}: {str(e)}",
                "query": query,
                "budget_inr": budget,
                "offers": [],
                "unverified_notes": []
            }

        offers = result.get("offers", [])
        unverified_notes = result.get("unverified_notes", [])

        # Log for purchase and checks dashboard
        log_search(query, budget, offers, unverified_notes)

        return {
            "success": True,
            "query": query,
            "budget_inr": budget,
            "offers": offers,
            "unverified_notes": unverified_notes
        }

    async def get_seller_explanation(self, seller: str, url: Optional[str] = None) -> str:
        """
        Agent Step 4:
        Calls explain_score on TRUSTMATE MCP server.
        """
        try:
            res = await self._call_mcp_tool("explain_score", {
                "seller": seller,
                "url": url or ""
            })
            return res.get("summary", "No explanation available for this seller.")
        except Exception as e:
            return f"Could not retrieve AI score explanation: {str(e)}"

agent = TrustmateAgent()

