#!/bin/bash

# Audio Comic Reader Startup Script

echo "🎭 Audio Comic Reader"
echo "===================="

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or not in PATH"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp env.example .env
    echo "📝 Please edit .env file and add your API keys:"
    echo "   - OPENAI_API_KEY for vision analysis"
    echo "   - MURF_API_KEY for text-to-speech"
    echo ""
    echo "Press Enter to continue or Ctrl+C to edit .env first..."
    read
fi

# Run tests
echo "🧪 Running component tests..."
python test_app.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🚀 Starting Audio Comic Reader..."
    echo "📱 Open your browser to: http://localhost:8000"
    echo "⏹️  Press Ctrl+C to stop the server"
    echo ""
    
    # Start the application
    python main.py
else
    echo "❌ Tests failed. Please fix the issues above."
    exit 1
fi 