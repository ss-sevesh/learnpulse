"""
LearnPulse AI Platform - Unified Launcher Script
Runs the FastAPI backend and Vite frontend concurrently.
"""
import sys
import subprocess
import time
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run_services():
    print("=" * 70)
    print("  LearnPulse: Local Learning Console")
    print("  Vector DB: local Qdrant | LLM: local Ollama")
    print("=" * 70)

    # 1. Start FastAPI backend
    print("\n[1/2] Starting FastAPI backend on http://127.0.0.1:8000 ...")
    backend_cmd = [
        sys.executable, "-m", "uvicorn", "src.backend.main:app",
        "--host", "127.0.0.1", "--port", "8000"
    ]
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(BASE_DIR))

    # Give backend a moment to bind
    time.sleep(2)

    # 2. Start React Vite frontend
    frontend_dir = BASE_DIR / "frontend"
    print("\n[2/2] Starting React Vite frontend on http://localhost:5173 ...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen([npm_cmd, "run", "dev"], cwd=str(frontend_dir))

    print("\n" + "=" * 70)
    print("  [OK] All services operational!")
    print("  [>] Frontend Web UI:  http://localhost:5173")
    print("  [>] Backend REST API: http://127.0.0.1:8000")
    print("  [>] OpenAPI Docs:     http://127.0.0.1:8000/docs")
    print("  Press Ctrl+C to terminate both servers.")
    print("=" * 70 + "\n")

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("Backend terminated unexpectedly.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend dev server terminated.")
                break
    except KeyboardInterrupt:
        print("\nShutting down services gracefully...")
    finally:
        for proc in [frontend_proc, backend_proc]:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        print("Shutdown complete.")

if __name__ == "__main__":
    run_services()
