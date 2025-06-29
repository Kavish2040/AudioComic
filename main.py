from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import os
import shutil
from pathlib import Path
import uuid
from typing import List, Dict, Any

from config import config
from services.pdf_processor import PDFProcessor
from services.vision_analyzer import VisionAnalyzer
from services.murf_tts import MurfTTSService
from services.comic_reader import ComicReader
from services.translation_service import TranslationService

# Create FastAPI app
app = FastAPI(title="Audio Comic Reader", version="1.0.0")

# Create necessary directories
os.makedirs(config.UPLOAD_DIR, exist_ok=True)
os.makedirs(config.TEMP_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/temp", StaticFiles(directory="temp"), name="temp")

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize services with error handling
pdf_processor = PDFProcessor()

# Initialize services that require API keys with proper error handling
try:
    vision_analyzer = VisionAnalyzer()
    print("✅ VisionAnalyzer initialized successfully")
except Exception as e:
    print(f"⚠️ Warning: VisionAnalyzer failed to initialize: {str(e)}")
    vision_analyzer = None

try:
    tts_service = MurfTTSService()
    print("✅ MurfTTSService initialized successfully")
except Exception as e:
    print(f"⚠️ Warning: MurfTTSService failed to initialize: {str(e)}")
    tts_service = None

translation_service = TranslationService()

# Initialize comic reader with available services
comic_reader = ComicReader(pdf_processor, vision_analyzer, tts_service)

# Store active sessions
active_sessions: Dict[str, Dict[str, Any]] = {}

@app.on_event("startup")
async def startup_event():
    """Print service status on startup"""
    print("🚀 Audio Comic Reader starting up...")
    print(f"🔍 Environment Debug:")
    print(f"   - OPENAI_API_KEY: {'Set' if config.OPENAI_API_KEY else 'NOT SET'}")
    print(f"   - MURF_API_KEY: {'Set' if config.MURF_API_KEY else 'NOT SET'}")
    print(f"   - DEBUG: {config.DEBUG}")
    print(f"   - PORT: {config.PORT}")
    print(f"✅ PDF Processor: Ready")
    print(f"{'✅' if vision_analyzer else '⚠️'} Vision Analyzer: {'Ready' if vision_analyzer else 'Not configured (missing OpenAI API key)'}")
    print(f"{'✅' if tts_service else '⚠️'} TTS Service: {'Ready' if tts_service else 'Not configured (missing Murf API key)'}")
    print(f"✅ Translation Service: Ready")
    print("🌐 Server is ready to accept requests!")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "services": {
            "vision_analyzer": vision_analyzer is not None,
            "tts_service": tts_service is not None,
            "translation_service": True,
            "pdf_processor": True
        },
        "environment": {
            "openai_api_key_configured": bool(config.OPENAI_API_KEY),
            "murf_api_key_configured": bool(config.MURF_API_KEY),
            "openai_key_length": len(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else 0,
            "murf_key_length": len(config.MURF_API_KEY) if config.MURF_API_KEY else 0
        }
    })

@app.get("/debug/env")
async def debug_environment():
    """Debug endpoint to check environment variables (remove in production)"""
    import os
    return JSONResponse({
        "environment_variables": {
            "OPENAI_API_KEY": "SET" if os.getenv("OPENAI_API_KEY") else "NOT SET",
            "MURF_API_KEY": "SET" if os.getenv("MURF_API_KEY") else "NOT SET",
            "PORT": os.getenv("PORT", "NOT SET"),
            "DEBUG": os.getenv("DEBUG", "NOT SET"),
        },
        "config_values": {
            "OPENAI_API_KEY": "SET" if config.OPENAI_API_KEY else "NOT SET",
            "MURF_API_KEY": "SET" if config.MURF_API_KEY else "NOT SET",
            "PORT": config.PORT,
            "DEBUG": config.DEBUG,
        }
    })

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with upload interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/languages")
async def get_supported_languages():
    """Get list of supported languages for translation"""
    languages = translation_service.get_supported_languages()
    return JSONResponse({
        "languages": languages,
        "default_language": "en-US"
    })

@app.post("/upload")
async def upload_comic(
    file: UploadFile = File(...),
    preferred_language: str = Form("en-US")
):
    """Upload and process comic PDF with language preference"""
    try:
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        if file.size > config.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Validate language
        if not translation_service.is_language_supported(preferred_language):
            raise HTTPException(status_code=400, detail=f"Unsupported language: {preferred_language}")
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_path = os.path.join(config.UPLOAD_DIR, f"{session_id}.pdf")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process PDF
        pages = await pdf_processor.extract_pages(file_path)
        
        # Store session data with language preference
        active_sessions[session_id] = {
            "file_path": file_path,
            "filename": file.filename,
            "pages": pages,
            "current_page": 0,
            "current_panel": 0,
            "panels": [],
            "preferred_language": preferred_language,
            "translated_panels": {}  # Cache for translated panel data
        }
        
        return JSONResponse({
            "session_id": session_id,
            "filename": file.filename,
            "total_pages": len(pages),
            "preferred_language": preferred_language,
            "language_name": translation_service.get_language_name(preferred_language),
            "message": "Comic uploaded successfully"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/comic/{session_id}")
async def get_comic_reader(request: Request, session_id: str):
    """Get comic reader interface"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = active_sessions[session_id]
    return templates.TemplateResponse("reader.html", {
        "request": request,
        "session_id": session_id,
        "filename": session_data["filename"],
        "total_pages": len(session_data["pages"])
    })

@app.post("/analyze-page/{session_id}/{page_num}")
async def analyze_page(session_id: str, page_num: int):
    """Analyze a specific page for panels and text"""
    try:
        print(f"🔍 Analyzing page {page_num} for session {session_id}")
        
        if session_id not in active_sessions:
            print(f"❌ Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = active_sessions[session_id]
        
        if page_num >= len(session_data["pages"]):
            print(f"❌ Invalid page number {page_num}, total pages: {len(session_data['pages'])}")
            raise HTTPException(status_code=400, detail="Invalid page number")
        
        # Get page image path
        page_image_path = session_data["pages"][page_num]
        print(f"📄 Analyzing image: {page_image_path}")
        
        # Check if image exists
        if not os.path.exists(page_image_path):
            print(f"❌ Image file not found: {page_image_path}")
            raise HTTPException(status_code=404, detail="Page image not found")
        
        # Get user's preferred language
        preferred_language = session_data.get("preferred_language", "en-US")
        print(f"🌐 Using language: {preferred_language}")
        
        # Analyze page with vision model and generate audio with proper voice selection
        print("🤖 Starting vision analysis and audio generation...")
        analysis = await comic_reader.analyze_and_generate_audio(
            page_image_path, 
            language_code=preferred_language
        )
        
        print(f"✅ Analysis complete. Found {len(analysis.get('panels', []))} panels")
        
        # Log panel details
        for i, panel in enumerate(analysis.get('panels', [])):
            text_elements = panel.get('text_elements', [])
            print(f"  Panel {i+1}: {len(text_elements)} text elements")
            print(f"    Text for speech: '{panel.get('text_for_speech', '')[:100]}...'")
            print(f"    Voice ID: {panel.get('voice_id', 'None')}")
            for j, text_elem in enumerate(text_elements):
                print(f"    Text {j+1}: '{text_elem.get('text', '')[:50]}...'")
        
        # Update session data
        session_data["current_page"] = page_num
        session_data["panels"] = analysis["panels"]
        session_data["current_panel"] = 0
        
        return JSONResponse(analysis)
        
    except Exception as e:
        print(f"❌ Error analyzing page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-audio/{session_id}")
async def generate_audio(
    session_id: str,
    text: str = Form(...),
    voice_id: str = Form("default"),
    gender: str = Form(None)
):
    """Generate audio for text using Murf AI"""
    try:
        print(f"🎤 Generating audio for session {session_id}")
        print(f"📝 Text: '{text[:100]}...'")
        print(f"🎵 Voice: {voice_id}")
        print(f"👤 Gender: {gender}")
        
        if session_id not in active_sessions:
            print(f"❌ Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate audio
        print("🔄 Calling TTS service...")
        audio_url = await tts_service.generate_speech(text, voice_id, gender=gender)
        
        print(f"✅ Audio generated: {audio_url}")
        
        return JSONResponse({
            "audio_url": audio_url,
            "text": text
        })
        
    except Exception as e:
        print(f"❌ Error generating audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/translate-and-generate-audio/{session_id}")
async def translate_and_generate_audio(
    session_id: str,
    text: str = Form(...),
    gender: str = Form("female")  # Default to female voice
):
    """Translate text to user's preferred language and generate audio"""
    try:
        print(f"🌐 Translating and generating audio for session {session_id}")
        print(f"📝 Original text: '{text[:100]}...'")
        print(f"👤 Gender preference: {gender}")
        
        if session_id not in active_sessions:
            print(f"❌ Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = active_sessions[session_id]
        preferred_language = session_data.get("preferred_language", "en-US")
        
        print(f"🎯 Target language: {preferred_language}")
        
        # Translate text to preferred language
        translation_result = await translation_service.translate_text([text], preferred_language)
        
        if not translation_result.get("translations"):
            raise Exception("Translation failed")
        
        translated_text = translation_result["translations"][0]["translated_text"]
        print(f"✅ Translated text: '{translated_text[:100]}...'")
        
        # Get appropriate voice for the language and gender
        voice_id = translation_service.get_voice_for_language(preferred_language, gender)
        if not voice_id:
            voice_id = "en-US-natalie"  # Fallback voice
        
        print(f"🎵 Using voice: {voice_id} (Gender: {gender})")
        
        # Generate audio with translated text
        audio_url = await tts_service.generate_speech(translated_text, voice_id, gender=gender)
        
        print(f"✅ Audio generated: {audio_url}")
        
        return JSONResponse({
            "audio_url": audio_url,
            "translated_text": translated_text,
            "language_name": translation_service.get_language_name(preferred_language),
            "voice_id": voice_id,
            "gender": gender
        })
        
    except Exception as e:
        print(f"❌ Error translating and generating audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/voices/{language_code}")
async def get_voices_for_language(language_code: str):
    """Get available voices for a specific language"""
    try:
        voices = translation_service.get_available_voices_for_language(language_code)
        return JSONResponse({
            "language": language_code,
            "language_name": translation_service.get_language_name(language_code),
            "voices": voices
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/all-voices")
async def get_all_voices():
    """Get all available voices for all languages"""
    try:
        all_voices = translation_service.get_all_voice_options()
        return JSONResponse({
            "voices": all_voices
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/translate-panels/{session_id}")
async def translate_panels(session_id: str, page_num: int):
    """Translate all panel text on a page to user's preferred language"""
    try:
        print(f"🌐 Translating panels for session {session_id}, page {page_num}")
        
        if session_id not in active_sessions:
            print(f"❌ Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = active_sessions[session_id]
        preferred_language = session_data.get("preferred_language", "en-US")
        
        if page_num >= len(session_data["pages"]):
            print(f"❌ Invalid page number {page_num}")
            raise HTTPException(status_code=400, detail="Invalid page number")
        
        # Check if panels are already analyzed
        if not session_data.get("panels"):
            print(f"❌ No panels found for page {page_num}")
            raise HTTPException(status_code=400, detail="Page not analyzed yet")
        
        # Check if already translated
        cache_key = f"page_{page_num}"
        if cache_key in session_data.get("translated_panels", {}):
            print(f"✅ Using cached translations for page {page_num}")
            return JSONResponse({
                "panels": session_data["translated_panels"][cache_key],
                "language": preferred_language,
                "language_name": translation_service.get_language_name(preferred_language)
            })
        
        # Extract all text from panels
        all_texts = []
        text_mapping = []  # Track which panel and text element each text belongs to
        
        for panel_idx, panel in enumerate(session_data["panels"]):
            for text_idx, text_elem in enumerate(panel.get("text_elements", [])):
                text = text_elem.get("text", "").strip()
                if text:
                    all_texts.append(text)
                    text_mapping.append({
                        "panel_idx": panel_idx,
                        "text_idx": text_idx,
                        "text_elem": text_elem
                    })
        
        if not all_texts:
            print(f"⚠️  No text found in panels on page {page_num}")
            return JSONResponse({
                "panels": session_data["panels"],
                "language": preferred_language,
                "language_name": translation_service.get_language_name(preferred_language)
            })
        
        print(f"📝 Translating {len(all_texts)} text elements to {preferred_language}")
        
        # Translate all texts
        translation_result = await translation_service.translate_text(all_texts, preferred_language)
        
        if not translation_result.get("translations"):
            raise Exception("Translation failed")
        
        # Create translated panels structure
        translated_panels = []
        for panel in session_data["panels"]:
            translated_panel = panel.copy()
            translated_text_elements = []
            
            for text_elem in panel.get("text_elements", []):
                original_text = text_elem.get("text", "").strip()
                if original_text:
                    # Find the translation for this text
                    for i, mapping in enumerate(text_mapping):
                        if (mapping["panel_idx"] == len(translated_panels) and 
                            mapping["text_elem"]["text"] == original_text):
                            translated_text = translation_result["translations"][i]["translated_text"]
                            translated_text_elem = text_elem.copy()
                            translated_text_elem["text"] = translated_text
                            translated_text_elem["original_text"] = original_text
                            translated_text_elements.append(translated_text_elem)
                            break
                    else:
                        # If no translation found, keep original
                        translated_text_elements.append(text_elem)
                else:
                    translated_text_elements.append(text_elem)
            
            translated_panel["text_elements"] = translated_text_elements
            translated_panels.append(translated_panel)
        
        # Cache the translated panels
        if "translated_panels" not in session_data:
            session_data["translated_panels"] = {}
        session_data["translated_panels"][cache_key] = translated_panels
        
        print(f"✅ Successfully translated {len(all_texts)} text elements")
        
        return JSONResponse({
            "panels": translated_panels,
            "language": preferred_language,
            "language_name": translation_service.get_language_name(preferred_language),
            "translated_count": len(all_texts)
        })
        
    except Exception as e:
        print(f"❌ Error translating panels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current session status"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = active_sessions[session_id]
    return JSONResponse({
        "current_page": session_data["current_page"],
        "current_panel": session_data["current_panel"],
        "total_pages": len(session_data["pages"]),
        "total_panels": len(session_data["panels"]),
        "filename": session_data["filename"],
        "preferred_language": session_data.get("preferred_language", "en-US"),
        "language_name": translation_service.get_language_name(session_data.get("preferred_language", "en-US"))
    })

@app.post("/session/{session_id}/navigate")
async def navigate_session(session_id: str, action: str):
    """Navigate through comic (next_panel, prev_panel, next_page, prev_page)"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = active_sessions[session_id]
    
    if action == "next_panel":
        if session_data["current_panel"] < len(session_data["panels"]) - 1:
            session_data["current_panel"] += 1
        elif session_data["current_page"] < len(session_data["pages"]) - 1:
            # Move to next page
            session_data["current_page"] += 1
            session_data["current_panel"] = 0
            session_data["panels"] = []  # Will need to analyze new page
    
    elif action == "prev_panel":
        if session_data["current_panel"] > 0:
            session_data["current_panel"] -= 1
        elif session_data["current_page"] > 0:
            # Move to previous page
            session_data["current_page"] -= 1
            session_data["current_panel"] = 0
            session_data["panels"] = []  # Will need to analyze previous page
    
    elif action == "next_page":
        if session_data["current_page"] < len(session_data["pages"]) - 1:
            session_data["current_page"] += 1
            session_data["current_panel"] = 0
            session_data["panels"] = []
    
    elif action == "prev_page":
        if session_data["current_page"] > 0:
            session_data["current_page"] -= 1
            session_data["current_panel"] = 0
            session_data["panels"] = []
    
    return JSONResponse({
        "current_page": session_data["current_page"],
        "current_panel": session_data["current_panel"],
        "action": action
    })

@app.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up session and associated files"""
    if session_id in active_sessions:
        session_data = active_sessions[session_id]
        
        # Remove uploaded file
        if os.path.exists(session_data["file_path"]):
            os.remove(session_data["file_path"])
        
        # Remove extracted pages
        for page_path in session_data["pages"]:
            if os.path.exists(page_path):
                os.remove(page_path)
        
        # Remove session
        del active_sessions[session_id]
    
    return JSONResponse({"message": "Session cleaned up successfully"})

if __name__ == "__main__":
    import uvicorn
    if config.DEBUG:
        uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
    else:
        uvicorn.run(app, host=config.HOST, port=config.PORT) 