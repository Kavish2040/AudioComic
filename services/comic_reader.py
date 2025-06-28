from typing import Dict, List, Any, Optional
import asyncio
import os
from pathlib import Path

from .pdf_processor import PDFProcessor
from .vision_analyzer import VisionAnalyzer
from .murf_tts import MurfTTSService

class ComicReader:
    """Main service that orchestrates comic reading functionality"""
    
    def __init__(self, pdf_processor: PDFProcessor, vision_analyzer: VisionAnalyzer, 
                 tts_service: MurfTTSService):
        self.pdf_processor = pdf_processor
        self.vision_analyzer = vision_analyzer
        self.tts_service = tts_service
    
    async def process_comic(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a comic PDF end-to-end
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing processed comic data
        """
        try:
            # Extract pages from PDF
            pages = await self.pdf_processor.extract_pages(pdf_path)
            
            # Get PDF info
            pdf_info = await self.pdf_processor.get_page_info(pdf_path)
            
            return {
                "pages": pages,
                "pdf_info": pdf_info,
                "total_pages": len(pages),
                "status": "ready_for_analysis"
            }
            
        except Exception as e:
            raise Exception(f"Error processing comic: {str(e)}")
    
    async def analyze_and_generate_audio(self, page_image_path: str, 
                                       voice_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze a comic page and generate audio for all panels
        
        Args:
            page_image_path: Path to the page image
            voice_settings: Optional voice settings for TTS
            
        Returns:
            Dictionary containing analysis and audio data
        """
        try:
            # Analyze the page
            analysis = await self.vision_analyzer.analyze_page(page_image_path)
            
            # Generate audio for each panel
            panels_with_audio = []
            
            for panel in analysis.get("panels", []):
                # Extract text for this panel
                panel_text = await self.vision_analyzer.get_panel_text(panel)
                
                # Generate audio if there's text
                audio_url = None
                if panel_text and panel_text.strip() and panel_text != "No text in this panel.":
                    # Determine voice based on text content
                    voice_id = self._determine_voice_for_panel(panel, voice_settings)
                    audio_url = await self.tts_service.generate_speech(panel_text, voice_id)
                
                # Add audio info to panel
                panel_with_audio = {
                    **panel,
                    "text_for_speech": panel_text,
                    "audio_url": audio_url,
                    "has_audio": audio_url is not None
                }
                
                panels_with_audio.append(panel_with_audio)
            
            # Update analysis with audio data
            analysis["panels"] = panels_with_audio
            analysis["total_panels_with_audio"] = sum(1 for p in panels_with_audio if p["has_audio"])
            
            return analysis
            
        except Exception as e:
            raise Exception(f"Error analyzing page and generating audio: {str(e)}")
    
    def _determine_voice_for_panel(self, panel: Dict[str, Any], 
                                 voice_settings: Optional[Dict[str, Any]] = None) -> str:
        """
        Determine the appropriate voice for a panel based on its content
        
        Args:
            panel: Panel data
            voice_settings: Optional voice settings override
            
        Returns:
            Voice ID to use for this panel
        """
        if voice_settings and voice_settings.get("voice_id"):
            return voice_settings["voice_id"]
        
        # Analyze text elements to determine character type
        text_elements = panel.get("text_elements", [])
        
        # Check for narration (use narrator voice)
        for element in text_elements:
            if element.get("type") == "narration":
                return "en-US-davis"  # Narrator voice
        
        # Check for sound effects (use dramatic voice)
        sound_effects = [e for e in text_elements if e.get("type") == "sound_effect"]
        if sound_effects and len(sound_effects) == len(text_elements):
            return "en-US-davis"  # Dramatic voice for sound effects
        
        # Default to main character voice
        return "en-US-aria"
    
    async def get_reading_session_data(self, session_id: str, page_num: int, 
                                     panel_num: int = 0) -> Dict[str, Any]:
        """
        Get data for a specific reading session position
        
        Args:
            session_id: Session identifier
            page_num: Current page number
            panel_num: Current panel number
            
        Returns:
            Reading session data
        """
        # This would typically interact with a database or session store
        # For now, return a basic structure
        return {
            "session_id": session_id,
            "current_page": page_num,
            "current_panel": panel_num,
            "reading_mode": "panel_by_panel",
            "auto_play": False
        }
    
    async def generate_page_summary_audio(self, analysis: Dict[str, Any]) -> str:
        """
        Generate audio summary for an entire page
        
        Args:
            analysis: Page analysis data
            
        Returns:
            URL to the generated summary audio
        """
        try:
            # Create a summary of the page
            page_summary = analysis.get("page_summary", "")
            
            if not page_summary:
                # Generate summary from panels
                panel_descriptions = []
                for panel in analysis.get("panels", []):
                    desc = panel.get("description", "")
                    if desc:
                        panel_descriptions.append(desc)
                
                if panel_descriptions:
                    page_summary = f"This page shows: {'. '.join(panel_descriptions)}"
                else:
                    page_summary = "This page contains visual content without readable text."
            
            # Generate audio for the summary
            audio_url = await self.tts_service.generate_speech(
                page_summary, 
                voice_id="en-US-davis"  # Use narrator voice for summaries
            )
            
            return audio_url
            
        except Exception as e:
            raise Exception(f"Error generating page summary audio: {str(e)}")
    
    async def cleanup_session_files(self, pages: List[str], audio_files: List[str] = None):
        """
        Clean up files associated with a session
        
        Args:
            pages: List of page image paths to clean up
            audio_files: Optional list of audio file paths to clean up
        """
        try:
            # Clean up page images
            self.pdf_processor.cleanup_pages(pages)
            
            # Clean up audio files if provided
            if audio_files:
                for audio_file in audio_files:
                    try:
                        # Convert URL path to file path
                        if audio_file.startswith("/static/audio/"):
                            file_path = audio_file.replace("/static/audio/", "static/audio/")
                            if os.path.exists(file_path):
                                os.remove(file_path)
                    except Exception as e:
                        print(f"Error cleaning up audio file {audio_file}: {e}")
            
        except Exception as e:
            print(f"Error during session cleanup: {e}") 