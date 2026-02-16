#!/bin/bash
# Antidote — Start Script
# Usage: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required. Install from python.org"
    exit 1
fi

# Check Python version (3.11+ required)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "Error: Python 3.11+ is required (found $PYTHON_VERSION)"
    exit 1
fi

# Check venv exists, create if not
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .
else
    source .venv/bin/activate
fi

# Check config exists
if [ ! -f "$HOME/.antidote/config.json" ]; then
    echo "No config found. Running setup wizard..."
    python3 wizard.py
fi

# Run Antidote
echo "Starting Antidote..."
antidote
