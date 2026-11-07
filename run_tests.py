"""
Direct test runner for Person B test suite
"""

import sys
import os

agent_dir = os.path.dirname(os.path.abspath(__file__))
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from tests.test_person_b_flow import (
    test_query_parsing,
    test_currency_conversion,
    test_mock_mcp_contract_shapes,
    test_mock_mcp_direct_tools,
    test_gating_logic,
    test_storage_and_dashboard
)

if __name__ == "__main__":
    print("Running Person B Test Suite...", flush=True)

    print("1. Testing query parsing...", end=" ", flush=True)
    test_query_parsing()
    print("PASSED", flush=True)

    print("2. Testing currency conversion (INR to USD)...", end=" ", flush=True)
    test_currency_conversion()
    print("PASSED", flush=True)

    print("3. Testing mock MCP contract shapes & gating...", end=" ", flush=True)
    test_mock_mcp_contract_shapes()
    print("PASSED", flush=True)

    print("4. Testing mock MCP direct tools (get_trust_score, explain_score)...", end=" ", flush=True)
    test_mock_mcp_direct_tools()
    print("PASSED", flush=True)

    print("5. Testing gating logic (< 2.5 score second confirm)...", end=" ", flush=True)
    test_gating_logic()
    print("PASSED", flush=True)

    print("6. Testing SQLite storage and dashboard persistence...", end=" ", flush=True)
    test_storage_and_dashboard()
    print("PASSED", flush=True)

    print("=======================================================", flush=True)
    print("🎉 ALL 6 TEST SUITES PASSED! PERSON B CONTRACT VERIFIED.", flush=True)
    print("=======================================================", flush=True)
