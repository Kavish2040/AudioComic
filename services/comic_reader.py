from typing import Dict, List, Any, Optional
import asyncio
import os
from pathlib import Path

from .pdf_processor import PDFProcessor
from .vision_analyzer import VisionAnalyzer
from .murf_tts import MurfTTSService

class ComicReader:
    """Main service that orchestrates comic reading functionality"""
    
    def __init__(self, pdf_processor: PDFProcessor, vision_analyzer: Optional[VisionAnalyzer], 
                 tts_service: Optional[MurfTTSService]):
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
                                       voice_settings: Optional[Dict[str, Any]] = None,
                                       language_code: str = "en-US") -> Dict[str, Any]:
        """
        Analyze a comic page and generate audio for all panels
        
        Args:
            page_image_path: Path to the page image
            voice_settings: Optional voice settings for TTS
            language_code: Language code for voice selection (e.g., 'en-US', 'es-ES')
            
        Returns:
            Dictionary containing analysis and audio data
        """
        try:
            # Check if vision analyzer is available
            if not self.vision_analyzer:
                return {
                    "panels": [{
                        "panel_id": 1,
                        "reading_order": 1,
                        "text_for_speech": "Vision analysis service not available. Please configure OpenAI API key.",
                        "audio_url": None,
                        "has_audio": False,
                        "voice_id": None,
                        "description": "Service unavailable"
                    }],
                    "page_summary": "Vision analysis service not configured",
                    "total_panels": 1,
                    "total_panels_with_audio": 0
                }
            
            # Analyze the page
            analysis = await self.vision_analyzer.analyze_page(page_image_path)
            
            # Generate audio for each panel
            panels_with_audio = []
            
            for panel in analysis.get("panels", []):
                # Extract text for this panel
                panel_text = await self.vision_analyzer.get_panel_text(panel)
                
                # Generate audio if there's text and TTS service is available
                audio_url = None
                voice_id = None
                if panel_text and panel_text.strip() and panel_text != "No text in this panel.":
                    # Determine voice based on text content and language
                    voice_id = self._determine_voice_for_panel(panel, voice_settings, language_code)
                    
                    # Generate audio only if TTS service is available
                    if self.tts_service:
                        try:
                            audio_url = await self.tts_service.generate_speech(panel_text, voice_id)
                        except Exception as e:
                            print(f"⚠️ TTS generation failed: {str(e)}")
                            audio_url = None
                
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
                                 voice_settings: Optional[Dict[str, Any]] = None,
                                 language_code: str = "en-US") -> str:
        """
        Determine the appropriate voice for a panel based on its content and language
        
        Args:
            panel: Panel data
            voice_settings: Optional voice settings override
            language_code: Language code for voice selection
            
        Returns:
            Voice ID to use for this panel
        """
        if voice_settings and voice_settings.get("voice_id"):
            return voice_settings["voice_id"]
        
        # Analyze text elements to determine character type
        text_elements = panel.get("text_elements", [])
        
        # Check for narration first (use narrator voice - male)
        for element in text_elements:
            if element.get("type") == "narration":
                print(f"🎭 Found narration, using narrator voice for {language_code}")
                return self._get_voice_for_language_and_gender(language_code, "male")
        
        # Check for sound effects (use dramatic voice - male)
        sound_effects = [e for e in text_elements if e.get("type") == "sound_effect"]
        if sound_effects and len(sound_effects) == len(text_elements):
            print(f"🎭 Only sound effects found, using narrator voice for {language_code}")
            return self._get_voice_for_language_and_gender(language_code, "male")
        
        # Find the primary speaking character (first speech element)
        primary_speaker = None
        for element in text_elements:
            if element.get("type") == "speech":
                primary_speaker = element.get("speaker", "").lower()
                break
        
        # If we have speaker information, use it directly
        if primary_speaker:
            print(f"🎭 Primary speaker identified: '{primary_speaker}'")
            gender = self._get_gender_from_speaker(primary_speaker)
            if gender:
                return self._get_voice_for_language_and_gender(language_code, gender)
        
        # Check panel description for character information
        panel_description = panel.get("description", "").lower()
        if panel_description:
            print(f"🎭 Analyzing panel description: '{panel_description[:100]}...'")
            
            # Look for character descriptions in the panel
            if any(phrase in panel_description for phrase in ["female character", "woman", "girl", "lady", "she", "her"]):
                print(f"🎭 Female character detected in panel description")
                return self._get_voice_for_language_and_gender(language_code, "female")
            elif any(phrase in panel_description for phrase in ["male character", "man", "boy", "guy", "he", "him"]):
                print(f"🎭 Male character detected in panel description")
                return self._get_voice_for_language_and_gender(language_code, "male")
            elif any(phrase in panel_description for phrase in ["child", "kid", "young"]):
                print(f"🎭 Child character detected in panel description")
                return self._get_voice_for_language_and_gender(language_code, "child")
        
        # Fallback: analyze all text content for gender indicators
        panel_text = " ".join([elem.get("text", "") for elem in text_elements]).lower()
        gender = self._analyze_character_gender(panel_text, text_elements)
        
        return self._get_voice_for_language_and_gender(language_code, gender)
    
    def _get_voice_for_language_and_gender(self, language_code: str, gender: str) -> str:
        """
        Get voice ID for a specific language and gender
        
        Args:
            language_code: Language code (e.g., 'en-US', 'es-ES')
            gender: Gender ('male', 'female', 'child')
            
        Returns:
            Voice ID for the language and gender
        """
        # Import here to avoid circular imports
        from .translation_service import TranslationService
        
        translation_service = TranslationService()
        
        # Handle child voices - default to female for child characters
        if gender == "child":
            gender = "female"
        
        # Get language-specific voice
        voice_id = translation_service.get_voice_for_language(language_code, gender)
        
        if voice_id:
            print(f"🎭 Selected {gender} voice for {language_code}: {voice_id}")
            return voice_id
        else:
            # Fallback to English if language not supported
            print(f"🎭 Language {language_code} not supported, falling back to English")
            fallback_voices = {
                "male": "en-US-miles",
                "female": "en-US-natalie"
            }
            return fallback_voices.get(gender, "en-US-natalie")

    def _get_gender_from_speaker(self, speaker: str) -> Optional[str]:
        """
        Get gender from speaker information
        
        Args:
            speaker: Speaker description from vision analysis
            
        Returns:
            Gender ('male', 'female', 'child') or None if not determined
        """
        speaker = speaker.lower().strip()
        
        # Direct gender matches - check for specific phrases
        if "female character" in speaker:
            print(f"🎭 Female character detected from speaker: '{speaker}'")
            return "female"
        
        if "male character" in speaker:
            print(f"🎭 Male character detected from speaker: '{speaker}'")
            return "male"
        
        # Check for other gender indicators
        if "woman" in speaker or "girl" in speaker or "lady" in speaker:
            print(f"🎭 Female gender detected from speaker: '{speaker}'")
            return "female"
        
        if "man" in speaker or "boy" in speaker or "guy" in speaker:
            print(f"🎭 Male gender detected from speaker: '{speaker}'")
            return "male"
        
        if "child" in speaker or "kid" in speaker:
            print(f"🎭 Child character detected from speaker: '{speaker}'")
            return "child"
        
        # Check for specific character names or titles
        male_titles = ["mr", "sir", "father", "dad", "son", "brother", "uncle", "grandfather"]
        female_titles = ["mrs", "ms", "miss", "mother", "mom", "daughter", "sister", "aunt", "grandmother"]
        
        for title in male_titles:
            if title in speaker:
                print(f"🎭 Male title detected in speaker: '{speaker}'")
                return "male"
        
        for title in female_titles:
            if title in speaker:
                print(f"🎭 Female title detected in speaker: '{speaker}'")
                return "female"
        
        return None
    
    def _analyze_character_gender(self, text: str, text_elements: List[Dict[str, Any]]) -> str:
        """
        Analyze text to determine character gender
        
        Args:
            text: Combined text from all elements
            text_elements: List of text elements with metadata
            
        Returns:
            Gender ('male', 'female', 'child')
        """
        print(f"🎭 Analyzing text for gender selection: '{text[:150]}...'")
        
        # Check for explicit gender phrases in the generated text (from get_panel_text)
        # Check female first to avoid substring matching issues
        if "female character says:" in text.lower():
            print(f"🎭 Found 'Female character says:' in text")
            return "female"
        
        if "male character says:" in text.lower():
            print(f"🎭 Found 'Male character says:' in text")
            return "male"
        
        # Check for explicit speaker information in text elements
        for element in text_elements:
            speaker = element.get("speaker", "").lower()
            if speaker and speaker != "unknown":
                # Check for gender indicators in speaker name
                if any(word in speaker for word in ["he", "him", "his", "man", "boy", "guy", "dude", "sir", "mr", "father", "dad", "son", "brother", "male"]):
                    print(f"🎭 Detected male speaker in element: {speaker}")
                    return "male"
                elif any(word in speaker for word in ["she", "her", "woman", "girl", "lady", "miss", "ms", "mrs", "mother", "mom", "daughter", "sister", "female"]):
                    print(f"🎭 Detected female speaker in element: {speaker}")
                    return "female"
                elif any(word in speaker for word in ["child", "kid", "baby", "young"]):
                    print(f"🎭 Detected child speaker in element: {speaker}")
                    return "child"
        
        # Analyze text content for gender indicators (including the full text)
        # Note: Put longer phrases first to avoid substring matching issues
        male_indicators = ["male character", "he", "him", "his", "man", "men", "boy", "boys", "guy", "guys", "dude", "father", "dad", "son", "brother", "uncle", "grandfather"]
        female_indicators = ["female character", "she", "her", "woman", "women", "girl", "girls", "lady", "ladies", "mother", "mom", "daughter", "sister", "aunt", "grandmother"]
        child_indicators = ["child", "children", "kid", "kids", "baby", "babies", "young", "little", "small"]
        
        # Count gender indicators
        male_count = sum(1 for word in male_indicators if word in text)
        female_count = sum(1 for word in female_indicators if word in text)
        child_count = sum(1 for word in child_indicators if word in text)
        
        print(f"🎭 Gender analysis - Male: {male_count}, Female: {female_count}, Child: {child_count}")
        
        # Decision logic with higher priority for explicit gender indicators
        if child_count > 0:
            print(f"🎭 Selected child gender")
            return "child"
        elif female_count > male_count:
            print(f"🎭 Selected female gender (female: {female_count} > male: {male_count})")
            return "female"
        elif male_count > female_count:
            print(f"🎭 Selected male gender (male: {male_count} > female: {female_count})")
            return "male"
        elif female_count > 0:
            print(f"🎭 Selected female gender (equal indicators, but female present)")
            return "female"
        elif male_count > 0:
            print(f"🎭 Selected male gender (equal indicators, but male present)")
            return "male"
        else:
            # Default: alternate between male and female for variety
            # Use text length to create some randomness
            if len(text) % 2 == 0:
                print(f"🎭 Selected default female gender (no clear indicators)")
                return "female"
            else:
                print(f"🎭 Selected default male gender (no clear indicators)")
                return "male"
    
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