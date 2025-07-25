#!/usr/bin/env python3
"""
TikTok Comments Crawler API Server Starter
Run from project root directory
"""

import uvicorn
import asyncio
import signal
import sys
import os
from pathlib import Path

def signal_handler(sig, frame):
    print('\n🛑 Server shutdown requested...')
    sys.exit(0)

def main():
    print("🎵 TikTok Comments Crawler API")
    print("=" * 40)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Change to backend_api directory
    backend_dir = Path("backend_api")
    if not backend_dir.exists():
        print("❌ Error: backend_api directory not found!")
        print("Please run this script from the project root directory")
        sys.exit(1)
    
    os.chdir(backend_dir)
    print(f"📂 Changed to directory: {backend_dir.absolute()}")
    
    # Ensure downloads directory exists
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    print(f"📁 Downloads directory: {downloads_dir.absolute()}")
    
    # Server configuration
    config = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,
        "reload_dirs": ["."],
        "log_level": "info",
        "access_log": True,
    }
    
    print(f"🚀 Starting server at http://{config['host']}:{config['port']}")
    print("📊 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("=" * 40)
    print("💡 Chrome Extension Setup:")
    print("   1. Load unpacked extension from chrome_extension/")
    print("   2. Visit TikTok video page")
    print("   3. Click floating button to crawl")
    print("=" * 40)
    
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 