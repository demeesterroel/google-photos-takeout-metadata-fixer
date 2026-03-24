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


def set_exif_gps(path: Path, lat: float, lon: float):
    """Set EXIF GPS using exiftool."""
    lat_ref = 'N' if lat >= 0 else 'S'
    lon_ref = 'E' if lon >= 0 else 'W'
    result = subprocess.run(
        ['exiftool', '-overwrite_original',
         f'-GPSLatitude={abs(lat)}',
         f'-GPSLatitudeRef={lat_ref}',
         f'-GPSLongitude={abs(lon)}',
         f'-GPSLongitudeRef={lon_ref}',
         str(path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error setting EXIF GPS: {result.stderr}")
        sys.exit(1)


def create_test_json(path: Path, timestamp: int, lat: float = 0.0, lon: float = 0.0, description: str = ""):
    """Create a Google Photos JSON sidecar file."""
    data = {
        "photoTakenTime": {"timestamp": str(timestamp)},
        "geoData": {"latitude": lat, "longitude": lon}
    }
    if description:
        data["description"] = description
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
    
    # Standard file with matching EXIF and JSON (no GPS)
    create_test_image(TEST_DATA_DIR / "correct.jpg")
    set_exif_date(TEST_DATA_DIR / "correct.jpg", "2024:01:15 09:30:00")
    create_test_json(TEST_DATA_DIR / "correct.jpg.json", 1705311000)
    print("  Created: correct.jpg (dates match, no GPS)")
    
    # File needing date update (no EXIF)
    create_test_image(TEST_DATA_DIR / "need_date.jpg")
    create_test_json(TEST_DATA_DIR / "need_date.jpg.json", 1705311000)
    print("  Created: need_date.jpg (no EXIF date)")
    
    # File needing date update (different dates)
    create_test_image(TEST_DATA_DIR / "wrong_date.jpg")
    set_exif_date(TEST_DATA_DIR / "wrong_date.jpg", "2024:01:20 10:00:00")
    create_test_json(TEST_DATA_DIR / "wrong_date.jpg.json", 1705311000)
    print("  Created: wrong_date.jpg (wrong EXIF date)")
    
    # Timezone difference (dates preserved)
    create_test_image(TEST_DATA_DIR / "timezone.jpg")
    set_exif_date(TEST_DATA_DIR / "timezone.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "timezone.jpg.json", 1705311000)
    print("  Created: timezone.jpg (1hr timezone diff)")
    
    # GPS only update (dates match, no EXIF GPS, JSON has GPS)
    create_test_image(TEST_DATA_DIR / "need_gps.jpg")
    set_exif_date(TEST_DATA_DIR / "need_gps.jpg", "2024:01:15 09:30:00")
    create_test_json(TEST_DATA_DIR / "need_gps.jpg.json", 1705311000, lat=51.5074, lon=-0.1278)
    print("  Created: need_gps.jpg (needs GPS only)")
    
    # GPS differs (dates match, EXIF GPS != JSON GPS)
    create_test_image(TEST_DATA_DIR / "gps_differs.jpg")
    set_exif_date(TEST_DATA_DIR / "gps_differs.jpg", "2024:01:15 09:30:00")
    set_exif_gps(TEST_DATA_DIR / "gps_differs.jpg", lat=48.8566, lon=2.3522)
    create_test_json(TEST_DATA_DIR / "gps_differs.jpg.json", 1705311000, lat=51.5074, lon=-0.1278)
    print("  Created: gps_differs.jpg (GPS differs)")
    
    # Both date and GPS need update
    create_test_image(TEST_DATA_DIR / "need_both.jpg")
    create_test_json(TEST_DATA_DIR / "need_both.jpg.json", 1705311000, lat=51.5074, lon=-0.1278)
    print("  Created: need_both.jpg (needs date and GPS)")
    
    # Timezone diff + GPS differs
    create_test_image(TEST_DATA_DIR / "tz_gps_diff.jpg")
    set_exif_date(TEST_DATA_DIR / "tz_gps_diff.jpg", "2024:01:15 10:30:00")
    set_exif_gps(TEST_DATA_DIR / "tz_gps_diff.jpg", lat=48.8566, lon=2.3522)
    create_test_json(TEST_DATA_DIR / "tz_gps_diff.jpg.json", 1705311000, lat=51.5074, lon=-0.1278)
    print("  Created: tz_gps_diff.jpg (timezone + GPS differs)")
    
    # GPS already correct (dates match, GPS matches)
    create_test_image(TEST_DATA_DIR / "gps_correct.jpg")
    set_exif_date(TEST_DATA_DIR / "gps_correct.jpg", "2024:01:15 09:30:00")
    set_exif_gps(TEST_DATA_DIR / "gps_correct.jpg", lat=51.5074, lon=-0.1278)
    create_test_json(TEST_DATA_DIR / "gps_correct.jpg.json", 1705311000, lat=51.5074, lon=-0.1278)
    print("  Created: gps_correct.jpg (GPS already correct)")
    
    # Edited file variant (-edited suffix)
    create_test_image(TEST_DATA_DIR / "photo-edited.jpg")
    set_exif_date(TEST_DATA_DIR / "photo-edited.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "photo.jpg.json", 1705311000)
    print("  Created: photo-edited.jpg + photo.jpg.json (-edited match)")
    
    # Truncated supplemental JSON
    create_test_image(TEST_DATA_DIR / "long_filename_test_image.jpg")
    set_exif_date(TEST_DATA_DIR / "long_filename_test_image.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "long_filename_test_image.jpg.supplemental-met.json", 1705311000)
    print("  Created: long_filename_test_image.jpg (truncated supplemental)")
    
    # Version file (~N suffix)
    create_test_image(TEST_DATA_DIR / "version~2.jpg")
    set_exif_date(TEST_DATA_DIR / "version~2.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "version.jpg.json", 1705311000)
    print("  Created: version~2.jpg + version.jpg.json (~N match)")
    
    # Duplicate file ((1) suffix)
    create_test_image(TEST_DATA_DIR / "duplicate(1).jpg")
    set_exif_date(TEST_DATA_DIR / "duplicate(1).jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "duplicate.jpg(1).json", 1705311000)
    print("  Created: duplicate(1).jpg + duplicate.jpg(1).json")
    
    # Bokeh/Portrait file (supplemental-metadata)
    create_test_image(TEST_DATA_DIR / "bokeh.jpg")
    set_exif_date(TEST_DATA_DIR / "bokeh.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "bokeh.jpg.supplemental-metadata.json", 1705311000)
    print("  Created: bokeh.jpg (supplemental-metadata)")
    
    # Truncated Bokeh supplemental
    create_test_image(TEST_DATA_DIR / "IMG_20240115_123000_Bokeh.jpg")
    set_exif_date(TEST_DATA_DIR / "IMG_20240115_123000_Bokeh.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "IMG_20240115_123000_Bokeh.jpg.supplemental-m.json", 1705311000)
    print("  Created: IMG_..._Bokeh.jpg (truncated Bokeh supplemental)")
    
    # No matching JSON
    create_test_image(TEST_DATA_DIR / "no_json.jpg")
    set_exif_date(TEST_DATA_DIR / "no_json.jpg", "2024:01:15 10:30:00")
    print("  Created: no_json.jpg (no matching JSON)")
    
    # Original UUID file
    create_test_image(TEST_DATA_DIR / "original_abc123_I.jpg")
    set_exif_date(TEST_DATA_DIR / "original_abc123_I.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "original_abc123_.json", 1705311000)
    print("  Created: original_abc123_I.jpg + original_abc123_.json")
    
    # Signal app truncated
    create_test_image(TEST_DATA_DIR / "signal-2024-01-15-12-00-00-123.jpg")
    set_exif_date(TEST_DATA_DIR / "signal-2024-01-15-12-00-00-123.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "signal-2024-01-15-12-00-00-123.jpg.supplementa.json", 1705311000)
    print("  Created: signal-...jpg (truncated supplemental)")
    
    # With description
    create_test_image(TEST_DATA_DIR / "with_desc.jpg")
    set_exif_date(TEST_DATA_DIR / "with_desc.jpg", "2024:01:15 09:30:00")
    create_test_json(TEST_DATA_DIR / "with_desc.jpg.json", 1705311000, description="Beach vacation")
    print("  Created: with_desc.jpg (with description)")
    
    print(f"\nTest data created successfully in {TEST_DATA_DIR}")
    print(f"Total files: {len(list(TEST_DATA_DIR.iterdir()))}")


if __name__ == "__main__":
    main()