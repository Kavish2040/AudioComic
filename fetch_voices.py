#!/usr/bin/env python3
"""
Script to fetch available voices from Murf AI API
"""

import asyncio
import aiohttp
import json
from config import config

async def fetch_voices():
    """Fetch all available voices from Murf AI"""
    if not config.MURF_API_KEY:
        print("❌ No Murf API key found. Please set MURF_API_KEY in your .env file")
        return
    
    headers = {
        "Accept": "application/json",
        "api-key": config.MURF_API_KEY
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.murf.ai/v1/speech/voices",
                headers=headers
            ) as response:
                if response.status == 200:
                    voices_data = await response.json()
                    print("✅ Successfully fetched voices from Murf AI")
                    
                    # Handle different response formats
                    if isinstance(voices_data, list):
                        voices_list = voices_data
                    elif isinstance(voices_data, dict) and 'voices' in voices_data:
                        voices_list = voices_data['voices']
                    else:
                        voices_list = voices_data
                    
                    print(f"📊 Total voices available: {len(voices_list)}")
                    
                    # Group voices by language
                    voices_by_language = {}
                    for voice in voices_list:
                        voice_id = voice.get('voiceId', '')
                        name = voice.get('name', '')
                        language = voice.get('language', '')
                        
                        if language not in voices_by_language:
                            voices_by_language[language] = []
                        
                        voices_by_language[language].append({
                            'voiceId': voice_id,
                            'name': name,
                            'language': language
                        })
                    
                    # Print voices by language
                    print("\n🎤 Available Voices by Language:")
                    print("=" * 60)
                    
                    for language, voices in sorted(voices_by_language.items()):
                        print(f"\n{language}:")
                        for voice in voices:
                            print(f"  - {voice['voiceId']} ({voice['name']})")
                    
                    # Save to file for reference
                    with open('available_voices.json', 'w') as f:
                        json.dump(voices_data, f, indent=2)
                    print(f"\n💾 Voice data saved to 'available_voices.json'")
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to fetch voices: {response.status} - {error_text}")
                    
    except Exception as e:
        print(f"❌ Error fetching voices: {e}")

if __name__ == "__main__":
    asyncio.run(fetch_voices()) 