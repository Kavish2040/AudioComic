#!/usr/bin/env python3
"""
Simple test script to verify the Audio Comic Reader application components
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from config import config
        print("✓ Config module imported successfully")
    except Exception as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    try:
        from services.pdf_processor import PDFProcessor
        print("✓ PDF processor imported successfully")
    except Exception as e:
        print(f"✗ PDF processor import failed: {e}")
        return False
    
    try:
        from services.vision_analyzer import VisionAnalyzer
        print("✓ Vision analyzer imported successfully")
    except Exception as e:
        print(f"✗ Vision analyzer import failed: {e}")
        return False
    
    try:
        from services.murf_tts import MurfTTSService
        print("✓ Murf TTS service imported successfully")
    except Exception as e:
        print(f"✗ Murf TTS import failed: {e}")
        return False
    
    try:
        from services.comic_reader import ComicReader
        print("✓ Comic reader imported successfully")
    except Exception as e:
        print(f"✗ Comic reader import failed: {e}")
        return False
    
    return True

def test_directories():
    """Test that required directories exist or can be created"""
    print("\nTesting directories...")
    
    directories = [
        "uploads",
        "temp", 
        "static",
        "static/audio",
        "templates"
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"✓ Directory '{directory}' ready")
        except Exception as e:
            print(f"✗ Failed to create directory '{directory}': {e}")
            return False
    
    return True

def test_templates():
    """Test that template files exist"""
    print("\nTesting templates...")
    
    templates = [
        "templates/base.html",
        "templates/index.html", 
        "templates/reader.html"
    ]
    
    for template in templates:
        if os.path.exists(template):
            print(f"✓ Template '{template}' exists")
        else:
            print(f"✗ Template '{template}' missing")
            return False
    
    return True

def test_config():
    """Test configuration settings"""
    print("\nTesting configuration...")
    
    from config import config
    
    # Check required settings
    if hasattr(config, 'HOST'):
        print(f"✓ Host configured: {config.HOST}")
    else:
        print("✗ Host not configured")
        return False
    
    if hasattr(config, 'PORT'):
        print(f"✓ Port configured: {config.PORT}")
    else:
        print("✗ Port not configured")
        return False
    
    if hasattr(config, 'UPLOAD_DIR'):
        print(f"✓ Upload directory configured: {config.UPLOAD_DIR}")
    else:
        print("✗ Upload directory not configured")
        return False
    
    # Check API keys (warn if missing but don't fail)
    if config.OPENAI_API_KEY:
        print("✓ OpenAI API key configured")
    else:
        print("⚠ OpenAI API key not configured (vision analysis will fail)")
    
    if config.MURF_API_KEY:
        print("✓ Murf API key configured")
    else:
        print("⚠ Murf API key not configured (TTS will use fallback)")
    
    return True

async def test_services():
    """Test service initialization"""
    print("\nTesting services...")
    
    try:
        from services.pdf_processor import PDFProcessor
        pdf_processor = PDFProcessor()
        print("✓ PDF processor initialized")
    except Exception as e:
        print(f"✗ PDF processor initialization failed: {e}")
        return False
    
    try:
        from services.vision_analyzer import VisionAnalyzer
        # This will fail without API key, but that's expected
        try:
            vision_analyzer = VisionAnalyzer()
            print("✓ Vision analyzer initialized")
        except ValueError as e:
            if "OpenAI API key is required" in str(e):
                print("⚠ Vision analyzer requires OpenAI API key")
            else:
                print(f"✗ Vision analyzer initialization failed: {e}")
                return False
    except Exception as e:
        print(f"✗ Vision analyzer import failed: {e}")
        return False
    
    try:
        from services.murf_tts import MurfTTSService
        # This will fail without API key, but that's expected
        try:
            tts_service = MurfTTSService()
            print("✓ Murf TTS service initialized")
        except ValueError as e:
            if "Murf AI API key is required" in str(e):
                print("⚠ Murf TTS service requires API key")
            else:
                print(f"✗ Murf TTS initialization failed: {e}")
                return False
    except Exception as e:
        print(f"✗ Murf TTS import failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("Audio Comic Reader - Component Test")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Directories", test_directories),
        ("Templates", test_templates),
        ("Configuration", test_config),
    ]
    
    all_passed = True
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                all_passed = False
        except Exception as e:
            print(f"✗ {test_name} test failed with exception: {e}")
            all_passed = False
    
    # Test services asynchronously
    try:
        if not asyncio.run(test_services()):
            all_passed = False
    except Exception as e:
        print(f"✗ Services test failed with exception: {e}")
        all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All tests passed! Application is ready to run.")
        print("\nTo start the application:")
        print("  python main.py")
        print("\nOr with uvicorn directly:")
        print("  uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 