"""
TRUSTMATE - Master Runner Script for Person B
Starts:
1. Mock TRUSTMATE MCP Server on http://127.0.0.1:8001
2. FastAPI Agent Backend API on http://127.0.0.1:8000
3. Next.js Frontend on http://127.0.0.1:3000
"""

import subprocess
import sys
import time
import os

def main():
    agent_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(agent_dir, "frontend")
    mock_script = os.path.join(agent_dir, "mock", "mock_mcp_server.py")
    main_script = os.path.join(agent_dir, "main.py")
    next_bin = os.path.join(frontend_dir, "node_modules", "next", "dist", "bin", "next")

    print("==================================================")
    print("  TRUSTMATE System Launcher (Person B)")
    print("==================================================")

    # 1. Start Mock MCP Server
    print("[1/3] Starting Mock TRUSTMATE MCP Server on http://127.0.0.1:8001...")
    p_mock = subprocess.Popen([sys.executable, mock_script], cwd=agent_dir)

    time.sleep(1.5)

    # 2. Start FastAPI Backend API
    print("[2/3] Starting FastAPI Agent Backend on http://127.0.0.1:8000...")
    p_backend = subprocess.Popen([sys.executable, main_script], cwd=agent_dir)

    time.sleep(1.5)

    # 3. Start Next.js Frontend
    print("[3/3] Starting Next.js Frontend on http://127.0.0.1:3000...")
    if os.path.exists(next_bin):
        p_frontend = subprocess.Popen(["node", next_bin, "dev", "-p", "3000"], cwd=frontend_dir)
    else:
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        p_frontend = subprocess.Popen([npm_cmd, "run", "dev"], cwd=frontend_dir)

    print("==================================================")
    print("  🚀 ALL SERVICES RUNNING SUCCESSFULLY!")
    print("  👉 Next.js UI:      http://127.0.0.1:3000")
    print("  👉 FastAPI Backend: http://127.0.0.1:8000")
    print("  👉 Mock MCP Server: http://127.0.0.1:8001")
    print("==================================================")

    try:
        p_frontend.wait()
    except KeyboardInterrupt:
        print("\nStopping all services...")
        p_mock.terminate()
        p_backend.terminate()
        p_frontend.terminate()

if __name__ == "__main__":
    main()
