#!/usr/bin/env python3
"""
TikTok Comments Crawler API Server Starter
"""

import uvicorn
import asyncio
import signal
import sys
from pathlib import Path
import os

# -- Path Setup: Start --
# This is the definitive fix for the ModuleNotFoundError.
# The server needs to know where the 'crawlers' package is.
# The 'crawlers' package lives inside the 'TikTok_CMT' directory.
# This code finds the project root, constructs the path to 'TikTok_CMT',
# and adds it to the Python path, allowing all imports to work correctly.
current_dir = Path(__file__).resolve().parent  # Resolves to backend_api's path
project_root = current_dir.parent             # Resolves to the project root
tiktok_cmt_dir = project_root / "TikTok_CMT"
sys.path.insert(0, str(tiktok_cmt_dir))
# -- Path Setup: End --

def signal_handler(sig, frame):
    print('\n🛑 Server shutdown requested...')
    sys.exit(0)

def main():
    print("🎵 TikTok Comments Crawler API")
    print("=" * 40)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ensure downloads directory exists
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    print(f"📁 Downloads directory: {downloads_dir.absolute()}")
    
    # Server configuration
    port = int(os.environ.get("PORT", 8000))
    config = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": port,
        "reload": False,
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