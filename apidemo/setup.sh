#!/bin/bash
# Quick setup script for VeloSim API Demo

set -e

echo "🚀 VeloSim API Demo Setup"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Found Python $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

# Generate client from local backup
echo "📦 Generating API client..."
python generate_client.py --local

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run dispatcher: python dispatcher.py"
echo ""
echo "Optional: Regenerate client from running backend"
echo "  python generate_client.py http://localhost:8000"
echo ""
echo ""
