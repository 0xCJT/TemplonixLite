#!/bin/bash
# ============================================================================
# Templonix Lite Launcher for macOS
# ============================================================================
# Double-click this file to start the Templonix Lite MCP server.
# You can also add this to your Dock for easy access.
#
# First-time setup:
#   1. Open Terminal
#   2. Run: chmod +x ~/Development/Templonix_Lite/config/start-templonix.command
#   3. If blocked by Gatekeeper, go to System Preferences > Security & Privacy
#      and click "Open Anyway"
# ============================================================================

# Configuration - Update this path if you installed Templonix elsewhere
PROJECT_ROOT="$HOME/Development/Templonix_Lite"

# Change to project directory
cd "$PROJECT_ROOT" || {
    echo "❌ Error: Could not find Templonix Lite at $PROJECT_ROOT"
    echo "Please update PROJECT_ROOT in this script to match your installation path."
    read -p "Press Enter to close..."
    exit 1
}

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Error: Virtual environment not found."
    echo "Please run bootstrap.sh first to set up the environment."
    read -p "Press Enter to close..."
    exit 1
fi

# Activate virtual environment and run the MCP server
echo "🚀 Starting Templonix Lite..."
echo "   Project: $PROJECT_ROOT"
echo "   Python:  .venv/bin/python"
echo ""

source .venv/bin/activate
python templonix_mcp/app.py

# Keep terminal open if there's an error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Templonix Lite exited with an error."
    read -p "Press Enter to close..."
fi
