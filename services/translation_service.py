import aiohttp
import json
import os
from typing import List, Dict, Any, Optional
from config import config

class TranslationService:
    """Service for translating text using Murf AI Translation API"""
    
    def __init__(self):
        if not config.MURF_API_KEY:
            print("⚠️  Warning: Murf AI API key not found. Translation will not be available.")
            self.api_key = None
        else:
            self.api_key = config.MURF_API_KEY
        
        self.api_url = "https://api.murf.ai/v1"
        
        # Supported languages mapping - Top 10 most common languages
        self.supported_languages = {
            "en-US": "English - US & Canada",
            "en-UK": "English - UK", 
            "es-ES": "Spanish - Spain",
            "es-MX": "Spanish - Mexico",
            "fr-FR": "French - France",
            "de-DE": "German - Germany",
            "it-IT": "Italian - Italy",
            "pt-BR": "Portuguese - Brazil",
            "zh-CN": "Chinese - China",
            "hi-IN": "Hindi - India"
        }
        
        # Language to voice mapping for TTS - Using correct voice IDs from Murf AI docs
        # Each language now has both male and female voice options
        self.language_voice_mapping = {
            "en-US": {
                "male": "en-US-miles",      # Miles (US English - Male)
                "female": "en-US-natalie"   # Natalie (US English - Female)
            },
            "en-UK": {
                "male": "en-UK-theo",       # Theo (UK English - Male)
                "female": "en-UK-ruby"      # Ruby (UK English - Female)
            },
            "es-ES": {
                "male": "es-ES-enrique",    # Enrique (Spanish - Spain - Male)
                "female": "es-ES-elvira"    # Elvira (Spanish - Spain - Female)
            },
            "es-MX": {
                "male": "es-MX-carlos",     # Carlos (Spanish - Mexico - Male)
                "female": "es-MX-valeria"   # Valeria (Spanish - Mexico - Female)
            },
            "fr-FR": {
                "male": "fr-FR-maxime",     # Maxime (French - France - Male)
                "female": "fr-FR-adélie"    # Adelie (French - France - Female)
            },
            "de-DE": {
                "male": "de-DE-matthias",   # Matthias (German - Germany - Male)
                "female": "de-DE-lia"       # Lia (German - Germany - Female)
            },
            "it-IT": {
                "male": "it-IT-lorenzo",    # Lorenzo (Italian - Italy - Male)
                "female": "it-IT-greta"     # Greta (Italian - Italy - Female)
            },
            "pt-BR": {
                "male": "pt-BR-heitor",     # Heitor (Portuguese - Brazil - Male)
                "female": "pt-BR-isadora"   # Isadora (Portuguese - Brazil - Female)
            },
            "zh-CN": {
                "male": "zh-CN-tao",        # Tao (Chinese - China - Male)
                "female": "zh-CN-jiao"      # Jiao (Chinese - China - Female)
            },
            "hi-IN": {
                "male": "hi-IN-kabir",      # Kabir (Hindi - India - Male)
                "female": "hi-IN-ayushi"    # Ayushi (Hindi - India - Female)
            }
        }
    
    async def translate_text(self, texts: List[str], target_language: str) -> Dict[str, Any]:
        """
        Translate text to target language using Murf AI Translation API
        
        Args:
            texts: List of texts to translate
            target_language: Target language code (e.g., 'es-ES', 'fr-FR')
            
        Returns:
            Dictionary containing translations and metadata
        """
        try:
            if not self.api_key:
                raise Exception("Murf AI API key not available")
            
            if target_language not in self.supported_languages:
                raise Exception(f"Unsupported language: {target_language}")
            
            # Prepare payload for Murf AI Translation API
            payload = {
                "target_language": target_language,
                "texts": texts
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "api-key": self.api_key
            }
            
            print(f"🌐 Translating {len(texts)} texts to {target_language}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/text/translate",
                    json=payload,
                    headers=headers
                ) as response:
                    
                    print(f"📡 Translation API response status: {response.status}")
                    
                    if response.status == 200:
                        response_data = await response.json()
                        print(f"✅ Translation successful. Translated {len(response_data.get('translations', []))} texts")
                        return response_data
                    else:
                        error_text = await response.text()
                        print(f"❌ Translation API error: {response.status} - {error_text}")
                        raise Exception(f"Translation API error: {response.status} - {error_text}")
                        
        except Exception as e:
            print(f"❌ Error translating text: {e}")
            # Return fallback translations (original text)
            return {
                "metadata": {
                    "character_count": {
                        "total_source_text_length": len(" ".join(texts)),
                        "total_translated_text_length": len(" ".join(texts))
                    },
                    "credits_used": 0,
                    "target_language": target_language
                },
                "translations": [
                    {
                        "source_text": text,
                        "translated_text": text  # Fallback to original text
                    }
                    for text in texts
                ]
            }
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported languages"""
        return self.supported_languages
    
    def get_voice_for_language(self, language_code: str, gender: str = "female") -> Optional[str]:
        """Get the appropriate voice ID for a given language and gender"""
        language_voices = self.language_voice_mapping.get(language_code)
        if isinstance(language_voices, dict):
            return language_voices.get(gender, language_voices.get("female"))
        # Fallback for old format
        return language_voices
    
    def get_available_voices_for_language(self, language_code: str) -> Dict[str, str]:
        """Get all available voices for a given language"""
        language_voices = self.language_voice_mapping.get(language_code)
        if isinstance(language_voices, dict):
            return language_voices
        # Fallback for old format
        return {"female": language_voices} if language_voices else {}
    
    def get_all_voice_options(self) -> Dict[str, Dict[str, str]]:
        """Get all voice options for all languages"""
        return self.language_voice_mapping
    
    def is_language_supported(self, language_code: str) -> bool:
        """Check if a language is supported"""
        return language_code in self.supported_languages
    
    def get_language_name(self, language_code: str) -> str:
        """Get the display name for a language code"""
        return self.supported_languages.get(language_code, language_code) 