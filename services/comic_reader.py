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
                # Process each text element individually for proper voice selection
                text_elements = panel.get("text_elements", [])
                combined_audio_parts = []
                combined_text_parts = []
                
                # If no text elements, use panel description
                description_speech_settings = None
                if not text_elements:
                    description = panel.get('description', '')
                    if description:
                        # Treat description as narration
                        description_speech_settings = self._determine_speech_settings_for_element(
                            {"type": "narration", "text": description}, 
                            panel, voice_settings, language_code
                        )
                        
                        panel_text = f"Scene: {description}"
                        combined_text_parts.append(panel_text)
                        
                        if self.tts_service:
                            try:
                                audio_url = await self.tts_service.generate_speech(
                                    panel_text,
                                    voice_id=description_speech_settings.get("voice_id"),
                                    style=description_speech_settings.get("style"),
                                    rate=description_speech_settings.get("rate", 0),
                                    pitch=description_speech_settings.get("pitch", 0)
                                )
                                combined_audio_parts.append(audio_url)
                            except Exception as e:
                                print(f"⚠️ TTS generation failed: {str(e)}")
                else:
                    # Group text elements by speaker to generate consistent voices
                    speaker_groups = {}
                    
                    # Group elements by speaker
                    for text_element in text_elements:
                        text_content = text_element.get('text', '').strip()
                        if not text_content:
                            continue
                        
                        speaker = text_element.get('speaker', 'Unknown')
                        if speaker not in speaker_groups:
                            speaker_groups[speaker] = []
                        speaker_groups[speaker].append(text_element)
                    
                    # Process each speaker group
                    for speaker, elements in speaker_groups.items():
                        # Determine voice settings for this speaker
                        first_element = elements[0]
                        speech_settings = self._determine_speech_settings_for_element(
                            first_element, panel, voice_settings, language_code
                        )
                        
                        # Combine all text from this speaker
                        speaker_texts = []
                        for element in elements:
                            formatted_text = self._format_text_element(element)
                            speaker_texts.append(formatted_text)
                            combined_text_parts.append(formatted_text)
                        
                        # Generate single audio for all text from this speaker
                        combined_speaker_text = '. '.join(speaker_texts)
                        
                        if self.tts_service:
                            try:
                                audio_url = await self.tts_service.generate_speech(
                                    combined_speaker_text,
                                    voice_id=speech_settings.get("voice_id"),
                                    style=speech_settings.get("style"),
                                    rate=speech_settings.get("rate", 0),
                                    pitch=speech_settings.get("pitch", 0)
                                )
                                combined_audio_parts.append(audio_url)
                            except Exception as e:
                                print(f"⚠️ TTS generation failed: {str(e)}")
                
                # Combine all text and use first audio URL (for compatibility)
                final_text = '. '.join(combined_text_parts) if combined_text_parts else "No text in this panel."
                final_audio = combined_audio_parts[0] if combined_audio_parts else None
                
                # Determine primary voice for this panel
                primary_voice = None
                primary_style = None
                primary_rate = 0
                primary_pitch = 0
                
                if text_elements:
                    # Use the voice settings from the first text element
                    first_element = text_elements[0]
                    speech_settings = self._determine_speech_settings_for_element(
                        first_element, panel, voice_settings, language_code
                    )
                    primary_voice = speech_settings.get("voice_id")
                    primary_style = speech_settings.get("style")
                    primary_rate = speech_settings.get("rate", 0)
                    primary_pitch = speech_settings.get("pitch", 0)
                elif description_speech_settings:
                    # Use description speech settings if no text elements
                    primary_voice = description_speech_settings.get("voice_id")
                    primary_style = description_speech_settings.get("style")
                    primary_rate = description_speech_settings.get("rate", 0)
                    primary_pitch = description_speech_settings.get("pitch", 0)
                
                # Add audio info to panel
                panel_with_audio = {
                    **panel,
                    "text_for_speech": final_text,
                    "audio_url": final_audio,
                    "has_audio": final_audio is not None,
                    "voice_id": primary_voice,              # Primary voice for frontend
                    "speech_style": primary_style,          # Primary style
                    "rate": primary_rate,                   # Primary rate
                    "pitch": primary_pitch,                 # Primary pitch
                    "audio_parts": combined_audio_parts,    # Store all audio parts
                    "text_parts": combined_text_parts,      # Store all text parts
                }
                
                panels_with_audio.append(panel_with_audio)
            
            # Update analysis with audio data
            analysis["panels"] = panels_with_audio
            analysis["total_panels_with_audio"] = sum(1 for p in panels_with_audio if p["has_audio"])
            
            return analysis
            
        except Exception as e:
            raise Exception(f"Error analyzing page and generating audio: {str(e)}")
    
    def _determine_speech_settings_for_element(self, text_element: Dict[str, Any], panel: Dict[str, Any],
                                             voice_settings: Optional[Dict[str, Any]] = None,
                                             language_code: str = "en-US") -> Dict[str, Any]:
        """
        Determine the appropriate voice, style, rate, and pitch for a specific text element with enhanced character distinction.
        
        Args:
            text_element: Individual text element from the panel
            panel: Panel data from vision analysis  
            voice_settings: Optional voice settings override from user
            language_code: Language code for voice selection
            
        Returns:
            Dictionary with voice_id, style, rate, and pitch
        """
        # Default settings
        settings = {
            "voice_id": None,
            "style": None,
            "rate": 0,
            "pitch": 0
        }

        # User override for voice
        if voice_settings and voice_settings.get("voice_id"):
            settings["voice_id"] = voice_settings["voice_id"]
        
        # Get text content for analysis
        text_content = text_element.get("text", "")
        panel_description = panel.get("description", "")
        text_type = text_element.get("type", "speech")
        speaker = text_element.get("speaker", "")
        
        # Analyze emotional content and visual cues
        emotional_analysis = self._analyze_emotional_content(panel_description, text_content)
        
        # Set style based on emotional analysis
        settings["style"] = emotional_analysis["style"]
        settings["rate"] = emotional_analysis["rate"] 
        settings["pitch"] = emotional_analysis["pitch"]
        
        # Enhanced character type detection and voice assignment
        character_type = self._analyze_character_type(speaker, text_content, text_type)
        
        # Get voice ID if not already set by user
        if not settings["voice_id"]:
            settings["voice_id"] = self._get_enhanced_voice_for_character(language_code, character_type, speaker)
        
        # Apply character-specific modulations
        character_modulation = self._get_character_modulation(character_type, text_type)
        settings["rate"] += character_modulation["rate_modifier"]
        settings["pitch"] += character_modulation["pitch_modifier"]
        
        # Ensure values stay within reasonable bounds
        settings["rate"] = max(-30, min(30, settings["rate"]))
        settings["pitch"] = max(-20, min(20, settings["pitch"]))
            
        print(f"🎭 Element voice: Speaker='{speaker}', Type='{character_type}', Voice='{settings['voice_id']}', Style='{settings['style']}', Rate='{settings['rate']}', Pitch='{settings['pitch']}'")
        return settings
    
    def _analyze_character_type(self, speaker: str, text_content: str, text_type: str) -> str:
        """
        Analyze character type for enhanced voice selection.
        
        Args:
            speaker: Speaker description
            text_content: Text content
            text_type: Type of text (speech, narration, etc.)
            
        Returns:
            Character type classification
        """
        speaker_lower = speaker.lower()
        text_lower = text_content.lower()
        
        # Narrator detection
        if text_type == "narration" or not speaker or "narrator" in speaker_lower:
            if any(word in text_lower for word in ["scene", "setting", "exterior", "interior", "meanwhile", "later"]):
                return "narrator_scene"
            return "narrator_general"
        
        # Child character detection (more specific)
        if any(word in speaker_lower for word in ["child", "kid", "baby", "little", "young", "teenager", "teen"]):
            return "child"
        
        # Elderly character detection
        if any(word in speaker_lower for word in ["old", "elderly", "grandpa", "grandma", "grandfather", "grandmother", "elder"]):
            return "elderly"
        
        # Authority figure detection
        if any(word in speaker_lower for word in ["officer", "police", "captain", "boss", "teacher", "doctor", "professor", "sir", "ma'am"]):
            return "authority"
        
        # Villain/antagonist detection
        if any(word in speaker_lower for word in ["villain", "enemy", "bad", "evil", "dark", "sinister"]):
            return "villain"
        
        # Hero/protagonist detection
        if any(word in speaker_lower for word in ["hero", "protagonist", "main", "leader"]):
            return "hero"
        
        # Gender-based classification
        if "female" in speaker_lower or any(word in speaker_lower for word in ["woman", "girl", "lady", "mother", "mom", "sister", "aunt"]):
            return "female"
        elif "male" in speaker_lower or any(word in speaker_lower for word in ["man", "boy", "guy", "father", "dad", "brother", "uncle"]):
            return "male"
        
        # Default to male for unclear cases
        return "male"
    
    def _get_enhanced_voice_for_character(self, language_code: str, character_type: str, speaker: str) -> str:
        """
        Get enhanced voice selection based on character type.
        
        Args:
            language_code: Language code
            character_type: Character type classification
            speaker: Original speaker description
            
        Returns:
            Voice ID optimized for character type
        """
        # Character type to voice mapping for English
        if language_code == "en-US":
            voice_mapping = {
                "narrator_scene": "en-US-ken",        # Deep, authoritative narrator
                "narrator_general": "en-US-ken",      # General narrator
                "male": "en-US-miles",                # Standard male voice
                "female": "en-US-natalie",            # Standard female voice
                "child": "en-US-natalie",             # Higher, younger voice
                "elderly": "en-US-ken",               # Deeper, more measured
                "authority": "en-US-ken",             # Authoritative voice
                "villain": "en-US-terrell",           # Deeper, more dramatic male
                "hero": "en-US-miles",                # Strong, confident male
            }
            
            selected_voice = voice_mapping.get(character_type, "en-US-miles")
            print(f"🎭 Character type '{character_type}' mapped to voice '{selected_voice}'")
            return selected_voice
        
        # Fallback to basic gender detection for other languages
        basic_gender = "female" if character_type in ["female", "child"] else "male"
        return self._get_voice_for_language_and_gender(language_code, basic_gender)
    
    def _get_character_modulation(self, character_type: str, text_type: str) -> Dict[str, int]:
        """
        Get character-specific voice modulation settings.
        
        Args:
            character_type: Character type classification
            text_type: Type of text
            
        Returns:
            Dictionary with rate and pitch modifiers
        """
        modulations = {
            "narrator_scene": {"rate_modifier": -8, "pitch_modifier": -3},      # Slower, lower for authority
            "narrator_general": {"rate_modifier": -5, "pitch_modifier": -2},    # Slightly slower and lower
            "child": {"rate_modifier": 5, "pitch_modifier": 8},                 # Faster, higher pitch
            "elderly": {"rate_modifier": -10, "pitch_modifier": -5},            # Slower, lower
            "authority": {"rate_modifier": -3, "pitch_modifier": -2},           # Slightly authoritative
            "villain": {"rate_modifier": -2, "pitch_modifier": -8},             # Slower, much lower
            "hero": {"rate_modifier": 2, "pitch_modifier": 2},                  # Slightly faster, confident
            "male": {"rate_modifier": 0, "pitch_modifier": 0},                  # Neutral
            "female": {"rate_modifier": 0, "pitch_modifier": 2},                # Slightly higher pitch
        }
        
        return modulations.get(character_type, {"rate_modifier": 0, "pitch_modifier": 0})
    
    def _format_text_element(self, text_element: Dict[str, Any]) -> str:
        """
        Format a text element for TTS based on its type and speaker.
        
        Args:
            text_element: Text element with type, text, and speaker
            
        Returns:
            Formatted text string for TTS
        """
        text_type = text_element.get('type', 'speech')
        text_content = text_element.get('text', '').strip()
        speaker = text_element.get('speaker', '')
        
        if text_type == 'speech':
            if speaker and speaker.lower() != 'unknown':
                return f"{speaker} says: {text_content}"
            else:
                return text_content
                
        elif text_type == 'thought':
            if speaker and speaker.lower() != 'unknown':
                return f"{speaker} thinks: {text_content}"
            else:
                return f"Thinking: {text_content}"
                
        elif text_type == 'narration':
            return text_content
            
        elif text_type == 'sound_effect':
            return f"Sound effect: {text_content}"
        
        return text_content

    def _determine_speech_settings(self, panel: Dict[str, Any], 
                                 voice_settings: Optional[Dict[str, Any]] = None,
                                 language_code: str = "en-US") -> Dict[str, Any]:
        """
        Determine the appropriate voice, style, rate, and pitch based on visual analysis.
        
        Args:
            panel: Panel data from vision analysis
            voice_settings: Optional voice settings override from user
            language_code: Language code for voice selection
            
        Returns:
            Dictionary with voice_id, style, rate, and pitch
        """
        # Default settings
        settings = {
            "voice_id": None,
            "style": None,
            "rate": 0,
            "pitch": 0
        }

        # User override for voice
        if voice_settings and voice_settings.get("voice_id"):
            settings["voice_id"] = voice_settings["voice_id"]
        
        # Get panel description and text for analysis
        panel_description = panel.get("description", "").lower()
        text_elements = panel.get("text_elements", [])
        panel_text = " ".join([elem.get("text", "") for elem in text_elements]).lower()
        
        # Analyze emotional content and visual cues
        emotional_analysis = self._analyze_emotional_content(panel_description, panel_text)
        
        # Set style based on emotional analysis
        settings["style"] = emotional_analysis["style"]
        
        # Set rate based on emotional intensity and content type
        settings["rate"] = emotional_analysis["rate"]
        
        # Set pitch based on character type and emotion
        settings["pitch"] = emotional_analysis["pitch"]
        
        # Determine gender and voice selection
        gender = self._determine_character_gender(panel_description, text_elements)
        
        # Get voice ID if not already set by user
        if not settings["voice_id"]:
            settings["voice_id"] = self._get_voice_for_language_and_gender(language_code, gender)
            
        print(f"🎭 Determined speech settings: Voice='{settings['voice_id']}', Style='{settings['style']}', Rate={settings['rate']}, Pitch={settings['pitch']}")
        return settings
    
    def _analyze_emotional_content(self, description: str, text: str) -> Dict[str, Any]:
        """
        Advanced emotional analysis to determine style, rate, and pitch with sophisticated voice modulation.
        
        Args:
            description: Panel description from vision analysis
            text: Text content from the panel
            
        Returns:
            Dictionary with style, rate, and pitch recommendations
        """
        # Initialize with defaults
        result = {
            "style": None,
            "rate": 0,
            "pitch": 0
        }
        
        # Combine description and text for analysis
        combined_text = f"{description} {text}".lower()
        
        # Advanced emotional intensity analysis with more nuanced categories
        emotional_keywords = {
            "furious": {
                "style": "Angry",
                "rate": 25,  # Very fast
                "pitch": 15,  # Higher pitch
                "keywords": ["furious", "rage", "enraged", "livid", "screaming", "shouting loudly", "yelling", "explosive", "violent"]
            },
            "angry": {
                "style": "Angry", 
                "rate": 15,  # Fast
                "pitch": 8,   # Slightly higher
                "keywords": ["angry", "mad", "irritated", "annoyed", "frustrated", "upset", "agitated", "stern", "harsh"]
            },
            "terrified": {
                "style": "Terrified",
                "rate": 30,  # Very fast
                "pitch": 20,  # Much higher pitch
                "keywords": ["terrified", "horrified", "panicked", "screaming in fear", "trembling", "petrified", "shocked", "gasping"]
            },
            "scared": {
                "style": "Terrified", 
                "rate": 20,  # Fast
                "pitch": 12,  # Higher
                "keywords": ["scared", "frightened", "afraid", "nervous", "worried", "anxious", "startled", "alarmed"]
            },
            "devastated": {
                "style": "Sad",
                "rate": -20,  # Very slow
                "pitch": -15, # Much lower
                "keywords": ["devastated", "heartbroken", "grief", "mourning", "sobbing", "crying heavily", "despair"]
            },
            "sad": {
                "style": "Sad",
                "rate": -10,  # Slow
                "pitch": -8,  # Lower
                "keywords": ["sad", "unhappy", "melancholy", "crying", "tears", "sorrow", "disappointed", "dejected"]
            },
            "ecstatic": {
                "style": "Promotional",
                "rate": 25,  # Very fast
                "pitch": 15,  # Higher
                "keywords": ["ecstatic", "thrilled", "overjoyed", "elated", "euphoric", "bursting with joy", "celebrating"]
            },
            "excited": {
                "style": "Promotional",
                "rate": 18,  # Fast
                "pitch": 10,  # Higher
                "keywords": ["excited", "enthusiastic", "energetic", "pumped", "animated", "vibrant", "lively"]
            },
            "happy": {
                "style": "Promotional", 
                "rate": 10,  # Slightly fast
                "pitch": 5,   # Slightly higher
                "keywords": ["happy", "joyful", "cheerful", "pleased", "content", "smiling", "laughing", "giggling"]
            },
            "mysterious": {
                "style": "Meditative",
                "rate": -15,  # Slow
                "pitch": -5,  # Slightly lower
                "keywords": ["mysterious", "secretive", "enigmatic", "shadowy", "hidden", "unknown", "cryptic"]
            },
            "romantic": {
                "style": "Calm",
                "rate": -8,   # Slow
                "pitch": -3,  # Slightly lower
                "keywords": ["romantic", "loving", "tender", "affectionate", "intimate", "passionate", "sweet"]
            },
            "dramatic": {
                "style": "Promotional",
                "rate": 12,  # Fast
                "pitch": 8,   # Higher
                "keywords": ["dramatic", "intense", "powerful", "climactic", "epic", "action-packed", "dynamic"]
            },
            "peaceful": {
                "style": "Calm",
                "rate": -18,  # Very slow
                "pitch": -8,  # Lower
                "keywords": ["peaceful", "serene", "tranquil", "calm", "relaxed", "gentle", "soothing", "quiet"]
            },
            "narrator_scene": {
                "style": "Narration",
                "rate": -12,  # Slower for better comprehension
                "pitch": -5,  # Slightly lower for authority
                "keywords": ["scene", "exterior", "interior", "setting", "location", "background", "environment", "meanwhile", "later", "earlier"]
            },
            "narrator_description": {
                "style": "Narration", 
                "rate": -8,   # Moderate slow
                "pitch": -2,  # Neutral with slight authority
                "keywords": ["description", "shows", "displays", "depicts", "illustrates", "reveals", "appears", "visible"]
            }
        }
        
        # Find the strongest emotional match with weighted scoring
        best_match = None
        highest_score = 0
        
        for emotion, config in emotional_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in config["keywords"]:
                if keyword in combined_text:
                    # Weight longer phrases more heavily
                    weight = len(keyword.split()) * 2 if len(keyword.split()) > 1 else 1
                    score += weight
                    matched_keywords.append(keyword)
            
            if score > highest_score:
                highest_score = score
                best_match = emotion
        
        # Apply the best matching emotional style
        if best_match and highest_score > 0:
            result["style"] = emotional_keywords[best_match]["style"]
            result["rate"] = emotional_keywords[best_match]["rate"]
            result["pitch"] = emotional_keywords[best_match]["pitch"]
            print(f"🎭 Emotion detected: {best_match} (score: {highest_score}) -> Style: {result['style']}, Rate: {result['rate']}, Pitch: {result['pitch']}")
        
        # Advanced special cases with context awareness
        
        # Sound effects - make them dramatic and attention-grabbing
        sound_effects = ["sound effect", "sfx", "bang", "boom", "crash", "pow", "zap", "whoosh", "slam", "thud", "splash", "buzz", "ring", "beep", "honk"]
        if any(word in combined_text for word in sound_effects):
            result["style"] = "Promotional"
            result["rate"] = 20
            result["pitch"] = 15
            print(f"🎭 Sound effect detected -> Enhanced dramatic style")
        
        # Internal thoughts - make them introspective and softer
        thought_indicators = ["thought", "thinking", "mind", "internal", "wonders", "remembers", "realizes", "considers"]
        if any(word in combined_text for word in thought_indicators):
            result["style"] = "Meditative"
            result["rate"] = -12
            result["pitch"] = -8
            print(f"🎭 Internal thought detected -> Meditative style")
        
        # Whispers and quiet speech - make them intimate and slow
        quiet_speech = ["whisper", "whispers", "quietly", "softly", "hushed", "murmur", "mumble", "under breath"]
        if any(word in combined_text for word in quiet_speech):
            result["style"] = "Calm"
            result["rate"] = -20
            result["pitch"] = -12
            print(f"🎭 Quiet speech detected -> Whisper style")
        
        # Exclamations and emphasis - make them more energetic
        exclamations = ["!", "!!", "!!!", "emphasized", "shouting", "exclaimed", "called out", "announced"]
        if any(word in combined_text for word in exclamations) or text.count('!') > 0:
            # Boost existing emotions or apply excited if no emotion detected
            if result["style"]:
                result["rate"] += 8
                result["pitch"] += 5
            else:
                result["style"] = "Promotional"
                result["rate"] = 15
                result["pitch"] = 8
            print(f"🎭 Exclamation detected -> Enhanced energy")
        
        # Questions - make them more inquisitive
        if "?" in text or any(word in combined_text for word in ["question", "asks", "wondering", "curious"]):
            if not result["style"]:  # Only if no emotion already detected
                result["style"] = "Promotional"
                result["rate"] = 5
                result["pitch"] = 3
            else:
                result["pitch"] += 3  # Add slight pitch increase for questioning tone
            print(f"🎭 Question detected -> Inquisitive tone")
        
        # Narrator-specific enhancements
        if any(word in combined_text for word in ["scene:", "setting:", "location:", "meanwhile", "later", "earlier", "exterior", "interior"]):
            result["style"] = "Narration"
            result["rate"] = -15  # Slower for narrator authority and clarity
            result["pitch"] = -6   # Lower for narrator gravitas
            print(f"🎭 Narrator scene setting detected -> Authoritative narration")
        
        return result
    
    def _determine_character_gender(self, description: str, text_elements: List[Dict[str, Any]]) -> str:
        """
        Determine character gender from visual description and text elements.
        
        Args:
            description: Panel description
            text_elements: Text elements from the panel
            
        Returns:
            Gender ('male', 'female', 'child')
        """
        # Check for explicit gender indicators in text elements
        for element in text_elements:
            speaker = element.get("speaker", "").lower()
            if speaker:
                detected_gender = self._get_gender_from_speaker(speaker)
                if detected_gender:
                    return detected_gender
        
        # Check description for visual gender cues
        description_lower = description.lower()
        
        # Female indicators
        if any(phrase in description_lower for phrase in [
            "female character", "woman", "women", "girl", "lady", "ladies", 
            "mother", "mom", "daughter", "sister", "aunt", "grandmother",
            "she", "her", "female", "feminine"
        ]):
            return "female"
        
        # Child indicators
        if any(phrase in description_lower for phrase in [
            "child", "children", "kid", "kids", "baby", "babies", "young", 
            "little", "small", "boy", "girl", "teenager", "teen"
        ]):
            return "child"
        
        # Male indicators (default)
        if any(phrase in description_lower for phrase in [
            "male character", "man", "men", "boy", "guy", "gentleman", 
            "father", "dad", "son", "brother", "uncle", "grandfather",
            "he", "his", "him", "male", "masculine"
        ]):
            return "male"
        
        # Default to male for narration or unclear cases
        return "male"
    
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

    async def generate_audio_for_session(self, session_id: str, voice_id: str = None, 
                                       style: str = None, rate: int = 0, pitch: int = 0) -> str:
        """
        Generate audio for the current session with specific voice settings
        
        Args:
            session_id: Session identifier
            voice_id: Specific voice ID to use
            style: Voice style (e.g., 'Conversational', 'Angry', 'Sad')
            rate: Speech rate adjustment (-50 to 50)
            pitch: Pitch adjustment (-50 to 50)
            
        Returns:
            URL to the generated audio
        """
        try:
            # This would typically get the current session data
            # For now, we'll use a placeholder text
            text = "Audio generation for session completed."
            
            if self.tts_service:
                audio_url = await self.tts_service.generate_speech(
                    text, 
                    voice_id=voice_id,
                    style=style,
                    rate=rate,
                    pitch=pitch
                )
                return audio_url
            else:
                return None
                
        except Exception as e:
            print(f"Error generating audio for session: {str(e)}")
            return None
    
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