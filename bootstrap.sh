#!/bin/bash
set -e

# ============================================================================
# Templonix Lite Bootstrap Script for macOS/Linux
# ============================================================================

echo ""
echo "============================================"
echo "  Templonix Lite - Bootstrap Setup"
echo "============================================"
echo ""

# ----------------------------------------------------------------------------
# Check Python version (require 3.10-3.13)
# ----------------------------------------------------------------------------
echo "Checking Python version..."

# Find python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    echo "   Please install Python 3.10-3.13 from https://www.python.org/downloads/"
    echo "   Or via Homebrew: brew install python@3.12"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$MAJOR" -ne 3 ]; then
    echo "❌ Error: Python 3 is required (found Python $MAJOR)"
    exit 1
fi

if [ "$MINOR" -lt 10 ]; then
    echo "❌ Error: Python 3.10 or higher is required (found Python $PYTHON_VERSION)"
    echo "   Please upgrade Python: https://www.python.org/downloads/"
    exit 1
fi

if [ "$MINOR" -gt 13 ]; then
    echo "❌ Error: Python $PYTHON_VERSION is too new"
    echo "   Python 3.14+ is not yet supported by all dependencies."
    echo ""
    echo "   Please install Python 3.12 instead:"
    echo "     macOS:  brew install python@3.12"
    echo "     Then:   /opt/homebrew/bin/python3.12 -m venv .venv"
    echo ""
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"
echo ""

# ----------------------------------------------------------------------------
# Create virtual environment
# ----------------------------------------------------------------------------
echo "Creating virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

# ----------------------------------------------------------------------------
# Install dependencies
# ----------------------------------------------------------------------------
echo "Upgrading pip..."
pip3 install --upgrade pip

echo ""
echo "Installing dependencies..."
pip3 install -r requirements.txt

# ----------------------------------------------------------------------------
# Done
# ----------------------------------------------------------------------------
echo ""
echo "============================================"
echo "  ✅ Bootstrap complete!"
echo "============================================"
echo ""
echo "  Ready to build Templonix Lite."
echo ""
echo "  Next steps:"
echo "    1. cd templonix_mcp"
echo "    2. cp mcp.mac.example.json manifest.json"
echo "    3. Edit manifest.json and replace USERNAME with: $(whoami)"
echo "    4. mcpb pack"
echo "    5. Install the .mcpb file in Claude Desktop"
echo ""