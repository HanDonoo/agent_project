#!/usr/bin/env python3
"""
Start the EC Skills Finder API server
"""
import sys
import subprocess
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Start the uvicorn server"""
    print("🚀 Starting EC Skills Finder API Server...")
    print("=" * 60)
    print("📍 API will be available at: http://localhost:8001")
    print("📚 API docs at: http://localhost:8001/docs")
    print("🔗 OpenWebUI endpoint: http://localhost:8001/v1/chat/completions")
    print("=" * 60)
    print()
    
    # Start uvicorn (use sys.executable to ensure correct Python interpreter)
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "EC_api.main:app",
        "--host", "0.0.0.0",
        "--port", "8001",
        "--reload"
    ])

if __name__ == "__main__":
    main()

