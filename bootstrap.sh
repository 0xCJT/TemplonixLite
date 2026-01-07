#!/bin/bash
set -e

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
pip3 install --upgrade pip

echo "Installing dependencies..."
pip3 install -r requirements.txt

echo "Bootstrap complete. Ready to build Templonix."