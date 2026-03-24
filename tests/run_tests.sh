#!/bin/bash
# Run unit tests for fix_metadata.py

# Check for dependencies
if ! command -v pytest &> /dev/null; then
    echo "Installing pytest..."
    pip install pytest
fi

# Check for exiftool
if ! command -v exiftool &> /dev/null; then
    echo "Error: exiftool is required but not installed."
    echo "Install with:"
    echo "  Ubuntu/Debian: sudo apt install libimage-exiftool-perl"
    echo "  macOS: brew install exiftool"
    exit 1
fi

# Run tests
cd "$(dirname "$0")"
pytest test_fix_metadata.py -v