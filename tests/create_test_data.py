#!/usr/bin/env python3
"""Create test data for fix_metadata.py unit tests."""
import json
import subprocess
import sys
from pathlib import Path

TEST_DATA_DIR = Path(__file__).parent / "test_data"


def create_test_image(path: Path, width: int = 100, height: int = 100):
    """Create a valid test image using PIL."""
    from PIL import Image
    img = Image.new('RGB', (width, height), color='red')
    img.save(str(path), 'JPEG', quality=85)


def set_exif_date(path: Path, exif_date: str):
    """Set EXIF date using exiftool."""
    result = subprocess.run(
        ['exiftool', '-overwrite_original', f'-DateTimeOriginal={exif_date}', str(path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error setting EXIF date: {result.stderr}")
        sys.exit(1)


def create_test_json(path: Path, timestamp: int, lat: float = 0.0, lon: float = 0.0):
    """Create a Google Photos JSON sidecar file."""
    data = {
        "photoTakenTime": {"timestamp": str(timestamp)},
        "geoData": {"latitude": lat, "longitude": lon}
    }
    path.write_text(json.dumps(data))


def main():
    try:
        from PIL import Image
    except ImportError:
        print("Error: PIL/Pillow not installed. Install with: pip install Pillow")
        sys.exit(1)
    
    if TEST_DATA_DIR.exists():
        print(f"Removing existing test data: {TEST_DATA_DIR}")
        import shutil
        shutil.rmtree(TEST_DATA_DIR)
    
    TEST_DATA_DIR.mkdir(parents=True)
    print(f"Creating test data in: {TEST_DATA_DIR}")
    
    create_test_image(TEST_DATA_DIR / "standard.jpg")
    set_exif_date(TEST_DATA_DIR / "standard.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "standard.jpg.json", 1705311000)
    print("  Created: standard.jpg + JSON")
    
    create_test_image(TEST_DATA_DIR / "no_exif.jpg")
    create_test_json(TEST_DATA_DIR / "no_exif.jpg.json", 1705311000)
    print("  Created: no_exif.jpg + JSON (no EXIF)")
    
    create_test_image(TEST_DATA_DIR / "timezone.jpg")
    set_exif_date(TEST_DATA_DIR / "timezone.jpg", "2024:01:15 11:30:00")
    create_test_json(TEST_DATA_DIR / "timezone.jpg.json", 1705311000)
    print("  Created: timezone.jpg + JSON (1hr difference)")
    
    create_test_image(TEST_DATA_DIR / "photo-edited.jpg")
    set_exif_date(TEST_DATA_DIR / "photo-edited.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "photo.jpg.json", 1705311000)
    print("  Created: photo-edited.jpg + photo.jpg.json (-edited match)")
    
    create_test_image(TEST_DATA_DIR / "long_filename_test_image.jpg")
    set_exif_date(TEST_DATA_DIR / "long_filename_test_image.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "long_filename_test_image.jpg.supplemental-met.json", 1705311000)
    print("  Created: long_filename_test_image.jpg (truncated supplemental)")
    
    create_test_image(TEST_DATA_DIR / "version~2.jpg")
    set_exif_date(TEST_DATA_DIR / "version~2.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "version.jpg.json", 1705311000)
    print("  Created: version~2.jpg + version.jpg.json (~N match)")
    
    create_test_image(TEST_DATA_DIR / "duplicate(1).jpg")
    set_exif_date(TEST_DATA_DIR / "duplicate(1).jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "duplicate.jpg(1).json", 1705311000)
    print("  Created: duplicate(1).jpg + duplicate.jpg(1).json")
    
    create_test_image(TEST_DATA_DIR / "bokeh.jpg")
    set_exif_date(TEST_DATA_DIR / "bokeh.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "bokeh.jpg.supplemental-metadata.json", 1705311000)
    print("  Created: bokeh.jpg (supplemental-metadata)")
    
    create_test_image(TEST_DATA_DIR / "IMG_20240115_123000_Bokeh.jpg")
    set_exif_date(TEST_DATA_DIR / "IMG_20240115_123000_Bokeh.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "IMG_20240115_123000_Bokeh.jpg.supplemental-m.json", 1705311000)
    print("  Created: IMG_..._Bokeh.jpg (truncated Bokeh supplemental)")
    
    create_test_image(TEST_DATA_DIR / "no_json.jpg")
    set_exif_date(TEST_DATA_DIR / "no_json.jpg", "2024:01:15 10:30:00")
    print("  Created: no_json.jpg (no matching JSON)")
    
    create_test_image(TEST_DATA_DIR / "with_gps.jpg")
    set_exif_date(TEST_DATA_DIR / "with_gps.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "with_gps.jpg.json", 1705311000, lat=51.5074, lon=-0.1278)
    print("  Created: with_gps.jpg (with GPS data)")
    
    create_test_image(TEST_DATA_DIR / "original_abc123_I.jpg")
    set_exif_date(TEST_DATA_DIR / "original_abc123_I.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "original_abc123_.json", 1705311000)
    print("  Created: original_abc123_I.jpg + original_abc123_.json")
    
    create_test_image(TEST_DATA_DIR / "signal-2024-01-15-12-00-00-123.jpg")
    set_exif_date(TEST_DATA_DIR / "signal-2024-01-15-12-00-00-123.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "signal-2024-01-15-12-00-00-123.jpg.supplementa.json", 1705311000)
    print("  Created: signal-...jpg (truncated supplemental)")
    
    print(f"\nTest data created successfully in {TEST_DATA_DIR}")
    print(f"Total files: {len(list(TEST_DATA_DIR.iterdir()))}")


if __name__ == "__main__":
    main()