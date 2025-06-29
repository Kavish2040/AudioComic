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
                    "has_audio": audio_url is not None,
                    "voice_id": voice_id  # Store the voice ID for display
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
        panel_text = " ".join([elem.get("text", "") for elem in text_elements]).lower()
        
        # Check for narration (use narrator voice)
        for element in text_elements:
            if element.get("type") == "narration":
                return "en-US-ken"  # Narrator voice
        
        # Check for sound effects (use dramatic voice)
        sound_effects = [e for e in text_elements if e.get("type") == "sound_effect"]
        if sound_effects and len(sound_effects) == len(text_elements):
            return "en-US-ken"  # Dramatic voice for sound effects
        
        # Analyze character gender and type from text content
        voice_id = self._analyze_character_voice(panel_text, text_elements)
        
        return voice_id
    
    def _analyze_character_voice(self, text: str, text_elements: List[Dict[str, Any]]) -> str:
        """
        Analyze text to determine character gender and choose appropriate voice
        
        Args:
            text: Combined text from all elements
            text_elements: List of text elements with metadata
            
        Returns:
            Voice ID to use
        """
        # Check for explicit speaker information
        for element in text_elements:
            speaker = element.get("speaker", "").lower()
            if speaker and speaker != "unknown":
                # Check for gender indicators in speaker name
                if any(word in speaker for word in ["he", "him", "his", "man", "boy", "guy", "dude", "sir", "mr", "father", "dad", "son", "brother", "male"]):
                    print(f"🎭 Detected male speaker: {speaker}")
                    return "en-US-miles"  # Male voice
                elif any(word in speaker for word in ["she", "her", "woman", "girl", "lady", "miss", "ms", "mrs", "mother", "mom", "daughter", "sister", "female"]):
                    print(f"🎭 Detected female speaker: {speaker}")
                    return "en-US-natalie"  # Female voice
                elif any(word in speaker for word in ["child", "kid", "baby", "young"]):
                    print(f"🎭 Detected child speaker: {speaker}")
                    return "en-US-river"  # Child-friendly voice
        
        # Analyze text content for gender indicators (including the full text)
        male_indicators = ["he", "him", "his", "man", "men", "boy", "boys", "guy", "guys", "dude", "father", "dad", "son", "brother", "uncle", "grandfather", "male character", "male"]
        female_indicators = ["she", "her", "woman", "women", "girl", "girls", "lady", "ladies", "mother", "mom", "daughter", "sister", "aunt", "grandmother", "female character", "female"]
        child_indicators = ["child", "children", "kid", "kids", "baby", "babies", "young", "little", "small"]
        
        # Count gender indicators
        male_count = sum(1 for word in male_indicators if word in text)
        female_count = sum(1 for word in female_indicators if word in text)
        child_count = sum(1 for word in child_indicators if word in text)
        
        print(f"🎭 Gender analysis - Male: {male_count}, Female: {female_count}, Child: {child_count}")
        print(f"🎭 Text being analyzed: '{text[:100]}...'")
        
        # Check for emotional content
        emotional_words = ["cry", "crying", "sad", "angry", "happy", "excited", "scared", "fear", "love", "hate"]
        is_emotional = any(word in text for word in emotional_words)
        
        # Decision logic with higher priority for explicit gender indicators
        if child_count > 0:
            print(f"🎭 Selected child voice (en-US-river)")
            return "en-US-river"  # Child-friendly voice
        elif male_count > 0:
            print(f"🎭 Selected male voice (en-US-miles)")
            return "en-US-miles"  # Male voice
        elif female_count > 0:
            print(f"🎭 Selected female voice (en-US-natalie)")
            return "en-US-natalie"  # Female voice
        elif is_emotional:
            print(f"🎭 Selected female voice for emotional content (en-US-natalie)")
            return "en-US-natalie"  # Female voice for emotional content
        else:
            # Default based on text length and content
            if len(text) > 100:  # Long text, likely narration
                print(f"🎭 Selected narrator voice (en-US-ken)")
                return "en-US-ken"  # Male narrator
            else:
                print(f"🎭 Selected default female voice (en-US-natalie)")
                return "en-US-natalie"  # Default to female voice
    
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
                voice_id="en-US-ken"  # Use narrator voice for summaries
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