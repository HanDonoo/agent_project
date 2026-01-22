#!/usr/bin/env python3
"""
Start the Company Employee Finder Agent API server
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from config import API_HOST, API_PORT, API_RELOAD, LOG_LEVEL


def main():
    print("=" * 60)
    print("Company Employee Finder Agent")
    print("=" * 60)
    print(f"Starting server on http://{API_HOST}:{API_PORT}")
    print(f"API Documentation: http://{API_HOST}:{API_PORT}/docs")
    print(f"Health Check: http://{API_HOST}:{API_PORT}/health")
    print("=" * 60)
    print("\nPress CTRL+C to stop the server\n")
    
    uvicorn.run(
        "api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD,
        log_level=LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()

