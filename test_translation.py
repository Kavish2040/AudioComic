#!/usr/bin/env python3
"""
Test script for translation functionality
"""

import asyncio
import os
from services.translation_service import TranslationService

async def test_translation():
    """Test the translation service"""
    print("🧪 Testing Translation Service...")
    
    # Initialize translation service
    translation_service = TranslationService()
    
    # Test 1: Get supported languages
    print("\n1. Testing supported languages...")
    languages = translation_service.get_supported_languages()
    print(f"✅ Found {len(languages)} supported languages")
    
    # Show first 5 languages
    for i, (code, name) in enumerate(list(languages.items())[:5]):
        print(f"   {code}: {name}")
    
    # Test 2: Check language support
    print("\n2. Testing language support...")
    test_languages = ["en-US", "es-ES", "fr-FR", "invalid-lang"]
    
    for lang in test_languages:
        is_supported = translation_service.is_language_supported(lang)
        print(f"   {lang}: {'✅ Supported' if is_supported else '❌ Not supported'}")
    
    # Test 3: Test voice mapping
    print("\n3. Testing voice mapping...")
    test_languages = ["en-US", "es-ES", "fr-FR"]
    
    for lang in test_languages:
        voice = translation_service.get_voice_for_language(lang)
        print(f"   {lang}: {voice or '❌ No voice found'}")
    
    # Test 4: Test translation (if API key is available)
    print("\n4. Testing translation...")
    if translation_service.api_key:
        test_texts = ["Hello, world!", "How are you today?"]
        target_language = "es-ES"
        
        try:
            result = await translation_service.translate_text(test_texts, target_language)
            print(f"✅ Translation successful!")
            print(f"   Target language: {result['metadata']['target_language']}")
            print(f"   Credits used: {result['metadata']['credits_used']}")
            
            for translation in result['translations']:
                print(f"   '{translation['source_text']}' → '{translation['translated_text']}'")
                
        except Exception as e:
            print(f"❌ Translation failed: {e}")
    else:
        print("⚠️  No API key available, skipping translation test")
    
    print("\n✅ Translation service test completed!")

if __name__ == "__main__":
    asyncio.run(test_translation()) 