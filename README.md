# TRUSTMATE: Agent & Customer Portal (Person B)

> **Build What's Next with PayPal and AI** | Submission Deadline: November 12, 2026

TRUSTMATE is a Truecaller-style authenticity and trust-verification agent for online shopping. Before a customer pays, TRUSTMATE calculates an independent trust score (1.0 to 5.0), surfaces key risk factors with tap-to-explain transparency, and enforces human-in-the-loop approval before processing payments securely via **PayPal**.

---

## 🏛 Decoupled Architecture (Person B Scope)

```
                       ┌─────────────────────────────────────┐
                       │     Next.js Frontend (React/JSX)    │
                       │     http://127.0.0.1:3000           │
                       │ ─────────────────────────────────── │
                       │ • Customer Search Box & Chips       │
                       │ • Trust-First Ranked Results Grid   │
                       │ • Tap-To-Explain Slide-Over Drawer  │
                       │ • High-Risk Warning Modal (<2.5)    │
                       │ • Purchase & Trust Audit Dashboard  │
                       └──────────────────┬──────────────────┘
                                          │
                            Proxied API calls (/api/*)
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    FastAPI Agent Backend (/agent-app) │
                      │    http://127.0.0.1:8000              │
                      │ ───────────────────────────────────── │
                      │  • Intent extraction (query + budget) │
                      │  • Strict Rank-Preservation           │
                      │  • Low-Score (<2.5) Gate Confirmation │
                      │  • Fixed INR->USD Demo Conversion     │
                      │  • SQLite Search & Order Audit Store  │
                      └───────────┬───────────────┬───────────┘
                                  │               │
                                  ▼               ▼
         ┌────────────────────────────────┐  ┌─────────────────────────────────┐
         │     TRUSTMATE MCP Server       │  │      PayPal Sandbox Engine      │
         │          (Person A)            │  │        (Person B Scope)         │
         │ ────────────────────────────── │  │ ─────────────────────────────── │
         │ • rank_offers (Trust-First)    │  │ • PayPal MCP JSON-RPC           │
         │ • get_trust_score              │  │ • PayPal Sandbox REST API       │
         │ • explain_score                │  │ • High-Fidelity Local Simulator │
         │ • SQLite Cache (3-Day TTL)     │  │ • Order Create & Capture Flow   │
         │ (HTTP endpoint: TRUST_MCP_URL) │  └─────────────────────────────────┘
         └────────────────────────────────┘
```

---

## ⚡ Ground Rules & Contract Alignment

- **Folder Boundary:** Person B works exclusively in `/agent-app`.
- **Frontend Isolation:** Next.js frontend is modularly isolated inside `/agent-app/frontend`.
- **Zero Re-scoring Rule:** Ranking and trust logic live strictly on Person A's server. Person B **never** alters the order or modifies scores returned by `rank_offers`.
- **Human-in-the-Loop:** Payment is never executed autonomously; the customer must explicitly click *"Approve & Pay with PayPal"*.
- **Low-Score Gating:** Any seller with `trust.score < 2.5` triggers a mandatory secondary warning dialog highlighting the authenticity risks before payment can be initiated.
- **Unrated Handling:** Null scores are clearly presented as **Unrated** with contextual notes, never penalized as a score of 1.

---

## 📦 What's Inside `/agent-app`

| Path | Purpose |
|---|---|
| `frontend/` | Next.js single-page application with identical Tailwind glassmorphic UI |
| `frontend/src/app/page.jsx` | React interactive UI, explain drawer, risk modal, dashboard & PayPal flow |
| `frontend/src/app/layout.jsx` | Next.js root layout with Plus Jakarta Sans & FontAwesome icons |
| `main.py` | FastAPI backend API routes: `/api/search`, `/api/explain`, `/api/order/*`, `/api/dashboard` |
| `agent.py` | Agent orchestrator: parses customer queries, calls `TRUST_MCP_URL`, preserves rankings |
| `paypal_client.py` | PayPal Sandbox integration: USD conversion, order creation, capture, and simulator fallback |
| `storage.py` | SQLite database logging search audits, trust checks, and captured PayPal transactions |
| `mock/mock_mcp_server.py` | Standalone mock MCP server returning contract-shaped test fixtures (Person A mock) |
| `run_all.py` | One-click launcher starting Mock MCP (8001), FastAPI Backend (8000), & Next.js Frontend (3000) |
| `tests/test_person_b_flow.py` | Test suite verifying contract shapes, parsing, gating, and orders |

---

## 🚀 Quickstart & Setup

### 1. Install Dependencies
```powershell
# Python API backend dependencies
pip install -r requirements.txt

# Next.js frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```ini
TRUST_MCP_URL=http://127.0.0.1:8001
PAYPAL_CLIENT_ID=your_paypal_sandbox_client_id_here
PAYPAL_CLIENT_SECRET=your_paypal_sandbox_client_secret_here
PAYPAL_MODE=simulator
```

### 3. Run Everything (One Command)
```powershell
python run_all.py
```
- **Next.js Frontend:** [http://127.0.0.1:3000](http://127.0.0.1:3000)
- **FastAPI Backend:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Mock MCP Server:** [http://127.0.0.1:8001](http://127.0.0.1:8001)

### 4. Switching to Person A's Real Server
When Person A deploys `/trust-mcp`, update `.env`:
```ini
TRUST_MCP_URL=https://your-person-a-render-service.onrender.com
```
Both the Next.js frontend and FastAPI backend automatically use Person A's live server without modifying any code.
