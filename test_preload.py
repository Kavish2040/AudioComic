#!/usr/bin/env python3
"""
Test script for PreloadManager functionality
"""

import asyncio
import time
from services.preload_manager import PreloadManager
from services.comic_reader import ComicReader
from services.pdf_processor import PDFProcessor
from services.vision_analyzer import VisionAnalyzer
from services.murf_tts import MurfTTSService

async def test_preload_manager():
    """Test the preload manager functionality"""
    print("🧪 Testing PreloadManager...")
    
    # Initialize services
    pdf_processor = PDFProcessor()
    
    try:
        vision_analyzer = VisionAnalyzer()
        print("✅ VisionAnalyzer initialized")
    except Exception as e:
        print(f"⚠️ VisionAnalyzer failed: {e}")
        vision_analyzer = None
    
    try:
        tts_service = MurfTTSService()
        print("✅ TTS Service initialized")
    except Exception as e:
        print(f"⚠️ TTS Service failed: {e}")
        tts_service = None
    
    comic_reader = ComicReader(pdf_processor, vision_analyzer, tts_service)
    
    # Initialize preload manager
    preload_manager = PreloadManager(comic_reader, max_workers=2, preload_ahead=2)
    
    # Start background processing (since we're in an async context)
    preload_manager.start_background_processing()
    
    # Simulate session data
    session_id = "test_session_123"
    pages = [
        "/path/to/page1.jpg",
        "/path/to/page2.jpg", 
        "/path/to/page3.jpg",
        "/path/to/page4.jpg"
    ]
    
    print(f"\n📋 Testing preload functionality for session {session_id}")
    print(f"📄 Total pages: {len(pages)}")
    
    # Test preloading upcoming pages from page 0
    print("\n🚀 Testing preload_upcoming_pages from page 0...")
    await preload_manager.preload_upcoming_pages(session_id, 0, pages, "en-US")
    
    # Wait a bit for processing
    print("⏳ Waiting for background processing...")
    await asyncio.sleep(2)
    
    # Check preload stats
    stats = preload_manager.get_preload_stats(session_id)
    print(f"📊 Preload stats: {stats}")
    
    # Test preloading from page 1
    print("\n🚀 Testing preload_upcoming_pages from page 1...")
    await preload_manager.preload_upcoming_pages(session_id, 1, pages, "en-US")
    
    # Wait a bit more
    await asyncio.sleep(2)
    
    # Check updated stats
    stats = preload_manager.get_preload_stats(session_id)
    print(f"📊 Updated preload stats: {stats}")
    
    # Test individual page status
    for page_num in range(4):
        status = preload_manager.get_preload_status(session_id, page_num)
        is_preloaded = preload_manager.is_page_preloaded(session_id, page_num)
        print(f"📄 Page {page_num}: status={status}, preloaded={is_preloaded}")
    
    # Test clearing session data
    print("\n🧹 Testing session cleanup...")
    preload_manager.clear_session_data(session_id)
    
    # Verify cleanup
    stats = preload_manager.get_preload_stats(session_id)
    print(f"📊 Stats after cleanup: {stats}")
    
    print("\n✅ PreloadManager test completed!")
    
    # Stop background processing
    preload_manager.stop_background_processing()

if __name__ == "__main__":
    asyncio.run(test_preload_manager()) 