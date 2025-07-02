# Audio Comic Reader

A professional web application that converts comic PDFs into interactive audio experiences using advanced AI technology. The app analyzes comic panels, extracts text, and generates natural-sounding audio narration with support for multiple languages.

## 🌟 Features

### Core Features
- **AI Vision Analysis**: Advanced computer vision technology analyzes comic panels, identifies speech bubbles, and determines the correct reading order
- **Natural Voice Synthesis**: High-quality text-to-speech with 50+ voice options and automatic gender detection
- **Interactive Reading**: Navigate panel by panel or page by page with synchronized audio playback
- **Professional UI**: Modern, responsive design with intuitive controls

### 🌐 Multi-Language Support (NEW!)
- **Text Translation**: Automatically translate comic text to 10 most common languages
- **Native Audio Narration**: Generate audio in the target language with native speaker voices
- **Language Selection**: Choose your preferred language at the start of each session
- **Real-time Translation**: Text is translated and audio is generated in your selected language

### ⚡ Smart Preloading (NEW!)
- **Background Processing**: Pages are analyzed and audio is generated in the background
- **Seamless Navigation**: No delays when moving between pages - everything is preloaded
- **Progress Tracking**: Real-time status updates showing preload progress
- **Resource Optimization**: Intelligent preloading of upcoming pages while current page plays

#### Supported Languages
- **English**: US, UK
- **Spanish**: Spain, Mexico
- **French**: France
- **German**: Germany
- **Italian**: Italy
- **Portuguese**: Brazil
- **Chinese**: China
- **Hindi**: India

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Murf AI API key (for text-to-speech and translation)
- OpenAI API key (for vision analysis)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd audio-comic-reader
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

5. **Open your browser**
   Navigate to `http://localhost:8000`

## 📖 How to Use

### Basic Usage
1. **Upload a Comic**: Drag and drop or select a PDF comic file
2. **Choose Language**: Select your preferred language for translation and audio
3. **Start Reading**: The app will automatically analyze and process your comic
4. **Enjoy**: Navigate through panels with synchronized audio narration

### Language Selection
- **Before Upload**: Select your preferred language from the dropdown menu
- **Translation**: All comic text will be automatically translated to your chosen language
- **Audio**: Narration will be generated in your selected language with native speaker voices
- **Display**: The current language is shown in the reader header

### Advanced Features
- **Auto-play**: Automatically play audio when selecting panels
- **Auto-advance**: Automatically move to the next panel when audio finishes
- **Voice Settings**: Adjust speed and pitch of audio narration
- **Page Summary**: Generate audio summaries of entire pages

## 🔧 Configuration

### Environment Variables
```bash
# Required API Keys
OPENAI_API_KEY=your_openai_api_key_here
MURF_API_KEY=your_murf_api_key_here

# Optional Settings
DEBUG=true
HOST=0.0.0.0
PORT=8000
MAX_FILE_SIZE_MB=50
```

### API Keys Setup
1. **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/)
   - Used for vision analysis and text extraction
2. **Murf AI API Key**: Get from [Murf AI](https://murf.ai/)
   - Used for text-to-speech and translation services

## 🧪 Testing

### Test Translation Functionality
```bash
python test_translation.py
```

This will test:
- Supported languages listing
- Language validation
- Voice mapping
- Translation API connectivity

## 🏗️ Architecture

### Services
- **PDFProcessor**: Extracts pages from PDF files
- **VisionAnalyzer**: Analyzes comic panels using OpenAI Vision API
- **MurfTTSService**: Generates speech using Murf AI
- **TranslationService**: Translates text using Murf AI Translation API
- **ComicReader**: Orchestrates the reading experience
- **PreloadManager**: Handles background processing and preloading of upcoming pages

### API Endpoints
- `POST /upload`: Upload comic with language preference
- `POST /analyze-page/{session_id}/{page_num}`: Analyze comic page
- `POST /translate-panels/{session_id}`: Translate panel text
- `POST /translate-and-generate-audio/{session_id}`: Translate and generate audio
- `GET /languages`: Get supported languages
- `GET /session/{session_id}/status`: Get session status with preload statistics
- `GET /session/{session_id}/preload-status/{page_num}`: Get preload status for specific page

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Murf AI** for text-to-speech and translation services
- **OpenAI** for vision analysis capabilities
- **FastAPI** for the web framework
- **Bootstrap** for the UI components
