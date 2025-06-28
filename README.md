# Audio Comic Reader

Transform your comic books into immersive audio experiences! This application uses AI to analyze comic pages, extract text from panels, and generate natural-sounding audio narration.

## Features

- **AI Vision Analysis**: Automatically detects comic panels and reading order
- **Text Extraction**: Identifies speech bubbles, narration, and sound effects
- **Natural Voice Synthesis**: High-quality text-to-speech with multiple voice options
- **Interactive Reading**: Panel-by-panel or page-by-page navigation
- **Responsive Design**: Works on desktop and mobile devices
- **Audio Controls**: Play, pause, download, and customize voice settings

## Prerequisites

- Python 3.8+
- OpenAI API key (for vision analysis)
- Murf AI API key (for text-to-speech)
- System dependencies for PDF processing:
  - `poppler-utils` (for pdf2image)
  - `espeak` or similar TTS engine (for fallback audio)

### Installing System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install poppler-utils espeak espeak-data libespeak1 libespeak-dev
```

**macOS:**
```bash
brew install poppler
brew install espeak
```

**Windows:**
- Download and install Poppler from: https://poppler.freedesktop.org/
- Add Poppler to your PATH
- espeak is optional for fallback TTS

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd audio-comic-reader
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` file and add your API keys:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   MURF_API_KEY=your_murf_api_key_here
   ```

## Usage

1. **Start the application:**
   ```bash
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Open your browser:**
   Navigate to `http://localhost:8000`

3. **Upload a comic:**
   - Click "Choose File" or drag and drop a PDF comic
   - Wait for processing (1-2 minutes for typical comics)
   - Use the interactive reader to navigate and listen

## API Endpoints

- `GET /` - Main upload page
- `POST /upload` - Upload and process comic PDF
- `GET /comic/{session_id}` - Comic reader interface
- `POST /analyze-page/{session_id}/{page_num}` - Analyze specific page
- `POST /generate-audio/{session_id}` - Generate audio for text
- `GET /session/{session_id}/status` - Get session status
- `POST /session/{session_id}/navigate` - Navigate through comic
- `DELETE /session/{session_id}` - Clean up session

## Project Structure

```
audio-comic-reader/
├── main.py                 # FastAPI application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── services/             # Core services
│   ├── __init__.py
│   ├── comic_reader.py   # Main orchestration service
│   ├── pdf_processor.py  # PDF to image conversion
│   ├── vision_analyzer.py # AI vision analysis
│   └── murf_tts.py       # Text-to-speech service
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Upload page
│   └── reader.html       # Comic reader interface
├── static/               # Static files (CSS, JS, audio)
├── uploads/              # Uploaded PDFs (temporary)
└── temp/                 # Extracted page images (temporary)
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY` - Required for vision analysis
- `MURF_API_KEY` - Required for high-quality TTS
- `MURF_API_URL` - Murf AI API endpoint (default: https://api.murf.ai/v1)
- `DEBUG` - Enable debug mode (default: false)
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)

### File Limits

- Maximum file size: 50MB
- Supported formats: PDF only
- Recommended: High-quality scanned comics with clear text

## Troubleshooting

### Common Issues

1. **"OpenAI API key is required"**
   - Make sure you've set `OPENAI_API_KEY` in your `.env` file
   - Verify your OpenAI account has API access

2. **"Murf AI API key is required"**
   - Set `MURF_API_KEY` in your `.env` file
   - The app will fall back to system TTS if Murf AI is unavailable

3. **PDF processing fails**
   - Ensure `poppler-utils` is installed
   - Check that the PDF is not corrupted or password-protected

4. **Poor text recognition**
   - Use high-quality scanned comics
   - Ensure text is clear and readable
   - Traditional comic layouts work best

### Performance Tips

- Comics with 10-20 pages process faster
- High DPI scans improve text recognition but increase processing time
- Clear session data regularly to free up disk space

## Development

### Running in Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Adding New Features

1. **New TTS Providers**: Extend `services/murf_tts.py`
2. **Vision Models**: Modify `services/vision_analyzer.py`
3. **UI Components**: Update templates in `templates/`
4. **API Endpoints**: Add routes in `main.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section above
- Review API documentation in the code
- Open an issue on GitHub

## Acknowledgments

- OpenAI for GPT-4 Vision API
- Murf AI for text-to-speech services
- FastAPI for the web framework
- Bootstrap for UI components # AudioComic
