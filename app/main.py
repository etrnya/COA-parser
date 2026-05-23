import os
import sys
import threading
import asyncio
import webview
from app.utils.logger import get_logger
import app.core.queue_db as queue_db
from app.bridge import WebviewBridge

logger = get_logger("Main")

# Global event loop for handling background async tasks
bg_loop = None

def start_async_loop(loop):
    """Run the asyncio event loop forever in a daemon thread."""
    asyncio.set_event_loop(loop)
    logger.info("Background Asyncio Loop starting...")
    loop.run_forever()

def main():
    global bg_loop
    
    logger.info("Starting COA Parser Application...")
    
    # 1. Initialize persistent queue database
    queue_db.init_db()
    
    # 2. Setup background async event loop thread
    bg_loop = asyncio.new_event_loop()
    t = threading.Thread(target=start_async_loop, args=(bg_loop,), daemon=True)
    t.start()
    
    # 3. Create Webview Bridge API
    bridge = WebviewBridge()
    bridge.set_loop(bg_loop)
    
    # 4. Determine HTML GUI path
    if getattr(sys, 'frozen', False):
        # In PyInstaller frozen state, static files are extracted to sys._MEIPASS
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    frontend_dir = os.path.join(base_dir, "frontend")
    index_html = os.path.join(frontend_dir, "index.html")
    
    if not os.path.exists(index_html):
        # Create a basic fallback html if frontend directory is empty
        os.makedirs(frontend_dir, exist_ok=True)
        with open(index_html, "w", encoding="utf-8") as f:
            f.write("<html><body><h1>COA Parser GUI Loading...</h1></body></html>")
            
    logger.info(f"Loading UI from: {index_html}")
    
    # 5. Create Desktop Window
    window = webview.create_window(
        title="AI COA 證書解析與驗證中心",
        url=index_html,
        js_api=bridge,
        width=1280,
        height=850,
        resizable=True,
        min_size=(1024, 700)
    )
    
    # Associate window with bridge
    bridge.set_window(window)
    
    # 6. Start Desktop Main Loop
    webview.start(debug=True)
    
    # Clean up loop when application exits
    logger.info("Application exiting, stopping background loops...")
    if bg_loop:
        bg_loop.call_soon_threadsafe(bg_loop.stop)

if __name__ == "__main__":
    main()
