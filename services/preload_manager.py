import asyncio
import threading
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import time
import logging

# Configure logging for preload manager
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PreloadManager:
    """
    Manages background preloading of comic pages for seamless reading experience.
    Preloads analysis and audio generation for upcoming pages while current page is playing.
    """
    
    def __init__(self, comic_reader, max_workers: int = 2, preload_ahead: int = 2):
        self.comic_reader = comic_reader
        self.max_workers = max_workers
        self.preload_ahead = preload_ahead  # How many pages ahead to preload
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.preload_queue = asyncio.Queue()
        self.preload_results: Dict[str, Dict[int, Any]] = {}  # session_id -> {page_num -> result}
        self.preload_status: Dict[str, Dict[int, str]] = {}  # session_id -> {page_num -> status}
        self.running = False
        self.background_task = None
        
        # Note: Background processing will be started when the event loop is available
        logger.info(f"🚀 PreloadManager initialized with {max_workers} workers, preloading {preload_ahead} pages ahead")
    
    def start_background_processing(self):
        """Start the background processing loop"""
        if not self.running:
            self.running = True
            self.background_task = asyncio.create_task(self._background_processor())
            logger.info("🚀 PreloadManager background processing started")
    
    def stop_background_processing(self):
        """Stop the background processing loop"""
        if self.running:
            self.running = False
            if self.background_task:
                self.background_task.cancel()
            logger.info("🛑 PreloadManager background processing stopped")
    
    async def _background_processor(self):
        """Background processing loop that handles preload requests"""
        while self.running:
            try:
                # Wait for preload requests
                request = await asyncio.wait_for(self.preload_queue.get(), timeout=1.0)
                
                session_id, page_num, page_image_path, language_code = request
                
                # Process the page in background
                await self._process_page_background(session_id, page_num, page_image_path, language_code)
                
                # Mark task as done
                self.preload_queue.task_done()
                
            except asyncio.TimeoutError:
                # No requests, continue loop
                continue
            except Exception as e:
                logger.error(f"❌ Error in background processor: {str(e)}")
                continue
    
    async def _process_page_background(self, session_id: str, page_num: int, 
                                     page_image_path: str, language_code: str):
        """Process a page in the background without blocking"""
        try:
            logger.info(f"🔄 Background processing page {page_num} for session {session_id}")
            
            # Update status to processing
            if session_id not in self.preload_status:
                self.preload_status[session_id] = {}
            self.preload_status[session_id][page_num] = "processing"
            
            # Run the analysis directly since it's already async
            analysis = await self._analyze_page_sync(page_image_path, language_code)
            
            # Store the result
            if session_id not in self.preload_results:
                self.preload_results[session_id] = {}
            self.preload_results[session_id][page_num] = analysis
            
            # Update status to completed
            self.preload_status[session_id][page_num] = "completed"
            
            logger.info(f"✅ Background processing completed for page {page_num}, session {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Background processing failed for page {page_num}, session {session_id}: {str(e)}")
            if session_id not in self.preload_status:
                self.preload_status[session_id] = {}
            self.preload_status[session_id][page_num] = "failed"
    
    async def _analyze_page_sync(self, page_image_path: str, language_code: str) -> Dict[str, Any]:
        """Synchronous wrapper for page analysis"""
        return await self.comic_reader.analyze_and_generate_audio(
            page_image_path, 
            language_code=language_code
        )
    
    async def preload_page(self, session_id: str, page_num: int, 
                          page_image_path: str, language_code: str = "en-US"):
        """
        Add a page to the preload queue for background processing
        
        Args:
            session_id: Session identifier
            page_num: Page number to preload
            page_image_path: Path to the page image
            language_code: Language code for processing
        """
        # Check if already preloaded or in progress
        if self.is_page_preloaded(session_id, page_num):
            logger.info(f"📋 Page {page_num} already preloaded for session {session_id}")
            return
        
        # Add to preload queue
        await self.preload_queue.put((session_id, page_num, page_image_path, language_code))
        logger.info(f"📋 Added page {page_num} to preload queue for session {session_id}")
    
    async def preload_upcoming_pages(self, session_id: str, current_page: int, 
                                   pages: List[str], language_code: str = "en-US"):
        """
        Preload upcoming pages based on current page position
        
        Args:
            session_id: Session identifier
            current_page: Current page number
            pages: List of page image paths
            language_code: Language code for processing
        """
        total_pages = len(pages)
        
        # Calculate which pages to preload
        pages_to_preload = []
        for i in range(1, self.preload_ahead + 1):
            next_page = current_page + i
            if next_page < total_pages:
                pages_to_preload.append((next_page, pages[next_page]))
        
        # Add pages to preload queue
        for page_num, page_image_path in pages_to_preload:
            await self.preload_page(session_id, page_num, page_image_path, language_code)
        
        logger.info(f"📋 Preloading {len(pages_to_preload)} pages ahead for session {session_id}")
    
    def is_page_preloaded(self, session_id: str, page_num: int) -> bool:
        """Check if a page is already preloaded"""
        return (session_id in self.preload_results and 
                page_num in self.preload_results[session_id])
    
    def get_preloaded_page(self, session_id: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Get preloaded page data if available"""
        if self.is_page_preloaded(session_id, page_num):
            return self.preload_results[session_id][page_num]
        return None
    
    def get_preload_status(self, session_id: str, page_num: int) -> str:
        """Get the status of a page preload operation"""
        if session_id in self.preload_status and page_num in self.preload_status[session_id]:
            return self.preload_status[session_id][page_num]
        return "not_started"
    
    def clear_session_data(self, session_id: str):
        """Clear all preload data for a session"""
        if session_id in self.preload_results:
            del self.preload_results[session_id]
        if session_id in self.preload_status:
            del self.preload_status[session_id]
        logger.info(f"🧹 Cleared preload data for session {session_id}")
    
    def get_preload_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics about preload operations for a session"""
        if session_id not in self.preload_status:
            return {
                "total_pages": 0,
                "completed": 0,
                "processing": 0,
                "failed": 0,
                "not_started": 0
            }
        
        statuses = self.preload_status[session_id]
        stats = {
            "total_pages": len(statuses),
            "completed": sum(1 for s in statuses.values() if s == "completed"),
            "processing": sum(1 for s in statuses.values() if s == "processing"),
            "failed": sum(1 for s in statuses.values() if s == "failed"),
            "not_started": sum(1 for s in statuses.values() if s == "not_started")
        }
        
        return stats 