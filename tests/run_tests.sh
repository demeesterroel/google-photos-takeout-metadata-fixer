#!/bin/bash
# Run unit tests for fix_metadata.py

# Check for dependencies
if ! command -v pytest &> /dev/null; then
    echo "Installing pytest..."
    pip install pytest --break-system-packages 2>/dev/null || pip install pytest
fi

if ! python3 -c "from PIL import Image" 2>/dev/null; then
    echo "Installing Pillow..."
    pip install Pillow --break-system-packages 2>/dev/null || pip install Pillow
fi

# Check for exiftool
if ! command -v exiftool &> /dev/null; then
    echo "Error: exiftool is required but not installed."
    echo "Install with:"
    echo "  Ubuntu/Debian: sudo apt install libimage-exiftool-perl"
    echo "  macOS: brew install exiftool"
    exit 1
fi

cd "$(dirname "$0")"

# Create test data if needed
if [ ! -d "test_data" ]; then
    echo "Creating test data..."
    python3 test_fix_metadata_setup.py
fi

# Run tests
echo ""
echo "Running tests..."
pytest test_fix_metadata.py -v