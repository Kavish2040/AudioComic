import aiohttp
import asyncio
import json
import os
from typing import Optional, Dict, Any
import uuid
from pathlib import Path

from config import config

class MurfTTSService:
    """Service for generating speech using Murf AI API"""
    
    def __init__(self):
        if not config.MURF_API_KEY:
            print("⚠️  Warning: Murf AI API key not found. Audio generation will use fallback methods.")
            self.api_key = None
        else:
            self.api_key = config.MURF_API_KEY
        
        self.api_url = config.MURF_API_URL
        self.audio_dir = os.path.join("static", "audio")
        
        # Create audio directory
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Default voice settings
        self.default_voice_settings = {
            "voice_id": "en-US-natalie",  # Default Murf AI voice
            "speed": 1.0,
            "pitch": 1.0,
            "emphasis": 1.0,
            "pause": 300  # milliseconds
        }
    
    def select_voice_for_gender(self, gender: str) -> str:
        """Return the Murf voiceId for the given gender."""
        if gender == "male":
            return "en-US-miles"
        return "en-US-natalie"

    async def generate_speech(self, text: str, voice_id: Optional[str] = None, 
                            settings: Optional[Dict[str, Any]] = None, gender: Optional[str] = None) -> str:
        """
        Generate speech audio from text using Murf AI
        
        Args:
            text: Text to convert to speech
            voice_id: Murf AI voice ID to use
            settings: Voice settings (speed, pitch, etc.)
            gender: Gender of the speaker
            
        Returns:
            URL path to the generated audio file
        """
        try:
            if not self.api_key:
                return await self._generate_fallback_audio(text)
            # Use gender-based voice if provided
            if gender:
                voice_id = self.select_voice_for_gender(gender)
            if not voice_id:
                voice_id = self.default_voice_settings["voice_id"]
            voice_settings = {**self.default_voice_settings}
            if settings:
                voice_settings.update(settings)
            audio_filename = f"audio_{uuid.uuid4().hex}.mp3"
            audio_path = os.path.join(self.audio_dir, audio_filename)
            payload = {
                "text": text,
                "voiceId": voice_id,
                "format": "MP3",
                "channelType": "MONO",
                "sampleRate": 44100
            }
            # Add optional settings if present
            if "rate" in voice_settings:
                payload["rate"] = voice_settings["rate"]
            if "pitch" in voice_settings:
                payload["pitch"] = voice_settings["pitch"]
            if "style" in voice_settings:
                payload["style"] = voice_settings["style"]
            if "variation" in voice_settings:
                payload["variation"] = voice_settings["variation"]
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "api-key": self.api_key
            }
            print(f"🎤 Generating audio for text: '{text[:50]}...' with voice: {voice_id}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://api.murf.ai/v1/speech/generate",
                    json=payload,
                    headers=headers
                ) as response:
                    print(f"📡 Murf AI API response status: {response.status}")
                    if response.status == 200:
                        response_data = await response.json()
                        if "audioFile" in response_data:
                            audio_url = response_data["audioFile"]
                            async with session.get(audio_url) as audio_response:
                                if audio_response.status == 200:
                                    audio_data = await audio_response.read()
                                    with open(audio_path, "wb") as f:
                                        f.write(audio_data)
                                    print(f"✅ Audio generated successfully: {audio_filename}")
                                    return f"/static/audio/{audio_filename}"
                                else:
                                    raise Exception(f"Failed to download audio file: {audio_response.status}")
                        else:
                            raise Exception("No audioFile URL in response")
                    else:
                        error_text = await response.text()
                        print(f"❌ Murf AI API error: {response.status} - {error_text}")
                        raise Exception(f"Murf AI API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Error generating speech with Murf AI: {e}")
            return await self._generate_fallback_audio(text)
    
    async def _generate_fallback_audio(self, text: str) -> str:
        """
        Generate fallback audio using system TTS or return text
        This is used when Murf AI is not available
        """
        try:
            print("🔄 Using fallback TTS method...")
            
            # Try to use system TTS as fallback
            import pyttsx3
            
            # Generate unique filename
            audio_filename = f"fallback_{uuid.uuid4().hex}.mp3"
            audio_path = os.path.join(self.audio_dir, audio_filename)
            
            # Initialize TTS engine
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)  # Speed
            engine.setProperty('volume', 0.9)  # Volume
            
            # Save audio
            engine.save_to_file(text, audio_path)
            engine.runAndWait()
            
            print(f"✅ Fallback audio generated: {audio_filename}")
            return f"/static/audio/{audio_filename}"
            
        except ImportError:
            print("⚠️  pyttsx3 not available, creating text placeholder...")
            # If pyttsx3 is not available, create a placeholder
            return await self._create_text_placeholder(text)
        
        except Exception as e:
            print(f"❌ Fallback TTS failed: {e}")
            return await self._create_text_placeholder(text)
    
    async def _create_text_placeholder(self, text: str) -> str:
        """Create a text placeholder when audio generation fails"""
        placeholder_filename = f"text_{uuid.uuid4().hex}.json"
        placeholder_path = os.path.join(self.audio_dir, placeholder_filename)
        
        # Save text as JSON for frontend to handle
        placeholder_data = {
            "type": "text_fallback",
            "text": text,
            "message": "Audio generation unavailable - text only"
        }
        
        with open(placeholder_path, "w") as f:
            json.dump(placeholder_data, f)
        
        return f"/static/audio/{placeholder_filename}"
    
    async def get_available_voices(self) -> Dict[str, Any]:
        """Get list of available Murf AI voices"""
        try:
            if not self.api_key:
                print("⚠️  No API key available, returning default voices")
                return self._get_default_voices()
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                async with session.get(
                    f"{self.api_url}/voices",
                    headers=headers
                ) as response:
                    
                    print(f"📡 Voices API response status: {response.status}")
                    
                    if response.status == 200:
                        voices_data = await response.json()
                        print(f"✅ Retrieved {len(voices_data.get('voices', []))} voices from Murf AI")
                        return voices_data
                    else:
                        error_text = await response.text()
                        print(f"❌ Error fetching voices: {response.status} - {error_text}")
                        # Return default voice options
                        return self._get_default_voices()
        
        except Exception as e:
            print(f"❌ Error fetching voices: {e}")
            return self._get_default_voices()
    
    def _get_default_voices(self) -> Dict[str, Any]:
        """Return default voice options when API is unavailable"""
        return {
            "voices": [
                {
                    "voice_id": "en-US-aria",
                    "name": "Aria",
                    "language": "English (US)",
                    "gender": "Female",
                    "description": "Clear and expressive female voice"
                },
                {
                    "voice_id": "en-US-davis",
                    "name": "Davis", 
                    "language": "English (US)",
                    "gender": "Male",
                    "description": "Professional male narrator voice"
                },
                {
                    "voice_id": "en-US-jenny",
                    "name": "Jenny",
                    "language": "English (US)", 
                    "gender": "Female",
                    "description": "Friendly and warm female voice"
                }
            ]
        }
    
    async def cleanup_audio_files(self, max_age_hours: int = 24):
        """Clean up old audio files to save disk space"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(self.audio_dir):
                file_path = os.path.join(self.audio_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        print(f"Cleaned up old audio file: {filename}")
        
        except Exception as e:
            print(f"Error during audio cleanup: {e}")
    
    def get_voice_settings_for_character(self, character_type: str) -> Dict[str, Any]:
        """Get appropriate voice settings based on character type"""
        character_voices = {
            "narrator": {
                "voice_id": "en-US-davis",
                "speed": 0.9,
                "pitch": 1.0,
                "emphasis": 1.1
            },
            "hero": {
                "voice_id": "en-US-aria", 
                "speed": 1.0,
                "pitch": 1.1,
                "emphasis": 1.2
            },
            "villain": {
                "voice_id": "en-US-davis",
                "speed": 0.8,
                "pitch": 0.8,
                "emphasis": 1.3
            },
            "child": {
                "voice_id": "en-US-jenny",
                "speed": 1.1,
                "pitch": 1.3,
                "emphasis": 1.0
            },
            "default": self.default_voice_settings
        }
        
        return character_voices.get(character_type, character_voices["default"]) 