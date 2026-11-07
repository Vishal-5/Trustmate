"""
TRUSTMATE - Database and Persistence (Person B)
Stores searches, trust checks, and captured PayPal orders for the Purchase Dashboard.
Uses SQLite for zero-configuration, cross-platform persistence.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "trustmate_agent.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table for past checks / searches
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            budget_inr REAL NOT NULL,
            offers_json TEXT NOT NULL,
            unverified_notes_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table for orders and payments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            capture_id TEXT,
            item_title TEXT NOT NULL,
            seller_name TEXT NOT NULL,
            amount_inr REAL NOT NULL,
            amount_usd REAL NOT NULL,
            trust_score REAL,
            trust_label TEXT,
            risk_confirmed INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            captured_at TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def log_search(query: str, budget_inr: float, offers: List[Dict[str, Any]], unverified_notes: List[str]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO search_checks (query, budget_inr, offers_json, unverified_notes_json) VALUES (?, ?, ?, ?)",
        (query, budget_inr, json.dumps(offers), json.dumps(unverified_notes))
    )
    conn.commit()
    conn.close()

def log_order_created(
    order_id: str,
    item_title: str,
    seller_name: str,
    amount_inr: float,
    amount_usd: float,
    trust_score: Optional[float],
    trust_label: str,
    risk_confirmed: bool = False
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO orders 
        (order_id, item_title, seller_name, amount_inr, amount_usd, trust_score, trust_label, risk_confirmed, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'CREATED')
        """,
        (order_id, item_title, seller_name, amount_inr, amount_usd, trust_score, trust_label, 1 if risk_confirmed else 0)
    )
    conn.commit()
    conn.close()

def log_order_captured(order_id: str, capture_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET capture_id = ?, status = 'COMPLETED', captured_at = ? WHERE order_id = ?",
        (capture_id, datetime.now().isoformat(), order_id)
    )
    conn.commit()
    conn.close()

def get_dashboard_data() -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 50")
    orders = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT id, query, budget_inr, unverified_notes_json, created_at FROM search_checks ORDER BY id DESC LIMIT 20")
    checks = []
    for row in cursor.fetchall():
        item = dict(row)
        try:
            item["unverified_notes"] = json.loads(item.get("unverified_notes_json") or "[]")
        except Exception:
            item["unverified_notes"] = []
        checks.append(item)

    conn.close()
    return {"orders": orders, "recent_searches": checks}

init_db()

