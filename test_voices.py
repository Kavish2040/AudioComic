#!/usr/bin/env python3
"""
Test script to verify voice IDs are working correctly with Murf AI
"""

import asyncio
import aiohttp
import json
from config import config

# Voice IDs from the updated translation service
VOICE_IDS = {
    "en-US": "en-US-natalie",
    "en-UK": "en-UK-ruby", 
    "es-ES": "es-ES-elvira",
    "es-MX": "es-MX-carlos",
    "fr-FR": "fr-FR-adélie",
    "de-DE": "de-DE-matthias",
    "it-IT": "it-IT-lorenzo",
    "pt-BR": "pt-BR-heitor",
    "zh-CN": "zh-CN-tao",
    "hi-IN": "hi-IN-kabir"
}

async def test_voice_id(voice_id: str, language: str):
    """Test if a voice ID is valid by making a simple TTS request"""
    if not config.MURF_API_KEY:
        print(f"❌ No Murf API key found. Skipping test for {language} ({voice_id})")
        return False
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "api-key": config.MURF_API_KEY
    }
    
    # Simple test payload
    payload = {
        "text": "Hello, this is a test.",
        "voiceId": voice_id,
        "outputFormat": "mp3",
        "sampleRate": 24000
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.murf.ai/v1/speech/generate",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    print(f"✅ {language} ({voice_id}): Voice ID is valid")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ {language} ({voice_id}): Invalid voice ID - {response.status} - {error_text}")
                    return False
    except Exception as e:
        print(f"❌ {language} ({voice_id}): Error testing voice ID - {e}")
        return False

async def main():
    """Test all voice IDs"""
    print("🔍 Testing voice IDs with Murf AI...")
    print("=" * 50)
    
    results = []
    for language, voice_id in VOICE_IDS.items():
        result = await test_voice_id(voice_id, language)
        results.append((language, voice_id, result))
        await asyncio.sleep(1)  # Rate limiting
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    valid_count = 0
    for language, voice_id, is_valid in results:
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"{language:12} | {voice_id:20} | {status}")
        if is_valid:
            valid_count += 1
    
    print(f"\nTotal: {len(results)} voices tested")
    print(f"Valid: {valid_count}")
    print(f"Invalid: {len(results) - valid_count}")
    
    if valid_count == len(results):
        print("\n🎉 All voice IDs are working correctly!")
    else:
        print(f"\n⚠️  {len(results) - valid_count} voice IDs need to be fixed")

if __name__ == "__main__":
    asyncio.run(main()) 