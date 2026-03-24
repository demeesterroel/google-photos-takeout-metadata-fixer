#!/usr/bin/env python3
"""Unit tests for fix_metadata.py"""
import json
import os
import shutil
import subprocess
from pathlib import Path
import pytest
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from fix_metadata import (
    find_json_for_file,
    parse_timestamp,
    is_timezone_difference,
    analyze_directory,
)

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
        pytest.fail(f"Failed to set EXIF date: {result.stderr}")


def create_test_json(path: Path, timestamp: int, lat: float = 0.0, lon: float = 0.0):
    """Create a Google Photos JSON sidecar file."""
    data = {
        "photoTakenTime": {"timestamp": str(timestamp)},
        "geoData": {"latitude": lat, "longitude": lon}
    }
    path.write_text(json.dumps(data))


def build_all_files_dict():
    """Build all_files dict like os.walk would (filename -> Path)."""
    all_files = {}
    for f in TEST_DATA_DIR.iterdir():
        all_files[f.name] = f
    return all_files


@pytest.fixture(scope="module")
def setup_test_data():
    """Set up test data directory with various scenarios."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("PIL/Pillow not installed, skipping tests")
    
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)
    TEST_DATA_DIR.mkdir(parents=True)
    
    create_test_image(TEST_DATA_DIR / "standard.jpg")
    set_exif_date(TEST_DATA_DIR / "standard.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "standard.jpg.json", 1705311000)
    
    create_test_image(TEST_DATA_DIR / "no_exif.jpg")
    create_test_json(TEST_DATA_DIR / "no_exif.jpg.json", 1705311000)
    
    create_test_image(TEST_DATA_DIR / "timezone.jpg")
    set_exif_date(TEST_DATA_DIR / "timezone.jpg", "2024:01:15 11:30:00")
    create_test_json(TEST_DATA_DIR / "timezone.jpg.json", 1705311000)
    
    create_test_image(TEST_DATA_DIR / "photo-edited.jpg")
    set_exif_date(TEST_DATA_DIR / "photo-edited.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "photo.jpg.json", 1705311000)
    
    create_test_image(TEST_DATA_DIR / "long_filename_test_image.jpg")
    set_exif_date(TEST_DATA_DIR / "long_filename_test_image.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "long_filename_test_image.jpg.supplemental-met.json", 1705311000)
    
    create_test_image(TEST_DATA_DIR / "version~2.jpg")
    set_exif_date(TEST_DATA_DIR / "version~2.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "version.jpg.json", 1705311000)
    
    create_test_image(TEST_DATA_DIR / "duplicate(1).jpg")
    set_exif_date(TEST_DATA_DIR / "duplicate(1).jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "duplicate.jpg(1).json", 1705311000)
    
    create_test_image(TEST_DATA_DIR / "bokeh.jpg")
    set_exif_date(TEST_DATA_DIR / "bokeh.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "bokeh.jpg.supplemental-metadata.json", 1705311000)
    
    create_test_image(TEST_DATA_DIR / "IMG_20240115_123000_Bokeh.jpg")
    set_exif_date(TEST_DATA_DIR / "IMG_20240115_123000_Bokeh.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "IMG_20240115_123000_Bokeh.jpg.supplemental-m.json", 1705311000)
    
    create_test_image(TEST_DATA_DIR / "no_json.jpg")
    set_exif_date(TEST_DATA_DIR / "no_json.jpg", "2024:01:15 10:30:00")
    
    create_test_image(TEST_DATA_DIR / "with_gps.jpg")
    set_exif_date(TEST_DATA_DIR / "with_gps.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "with_gps.jpg.json", 1705311000, lat=51.5074, lon=-0.1278)
    
    create_test_image(TEST_DATA_DIR / "original_abc123_I.jpg")
    set_exif_date(TEST_DATA_DIR / "original_abc123_I.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "original_abc123_.json", 1705311000)
    
    create_test_image(TEST_DATA_DIR / "signal-2024-01-15-12-00-00-123.jpg")
    set_exif_date(TEST_DATA_DIR / "signal-2024-01-15-12-00-00-123.jpg", "2024:01:15 10:30:00")
    create_test_json(TEST_DATA_DIR / "signal-2024-01-15-12-00-00-123.jpg.supplementa.json", 1705311000)
    
    yield build_all_files_dict()
    
    shutil.rmtree(TEST_DATA_DIR)


class TestFindJsonForFile:
    """Tests for find_json_for_file function."""
    
    def test_standard_match(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["standard.jpg"], all_files)
        assert result is not None
        assert result.name == "standard.jpg.json"
    
    def test_supplemental_metadata(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["bokeh.jpg"], all_files)
        assert result is not None
        assert "supplemental" in result.name
    
    def test_truncated_supplemental(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["long_filename_test_image.jpg"], all_files)
        assert result is not None
    
    def test_edited_suffix(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["photo-edited.jpg"], all_files)
        assert result is not None
    
    def test_version_tilde(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["version~2.jpg"], all_files)
        assert result is not None
    
    def test_duplicate_number(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["duplicate(1).jpg"], all_files)
        assert result is not None
    
    def test_no_json_returns_none(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["no_json.jpg"], all_files)
        assert result is None
    
    def test_bokeh_suffix(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["IMG_20240115_123000_Bokeh.jpg"], all_files)
        assert result is not None
    
    def test_original_uuid_I(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["original_abc123_I.jpg"], all_files)
        assert result is not None
    
    def test_signal_truncated(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["signal-2024-01-15-12-00-00-123.jpg"], all_files)
        assert result is not None


class TestParseTimestamp:
    """Tests for parse_timestamp function."""
    
    def test_valid_timestamp(self):
        result = parse_timestamp("1705311000")
        assert result == "2024:01:15 09:30:00"
    
    def test_invalid_timestamp(self):
        result = parse_timestamp("invalid")
        assert result is None
    
    def test_empty_timestamp(self):
        result = parse_timestamp("")
        assert result is None


class TestTimezoneDifference:
    """Tests for is_timezone_difference function."""
    
    def test_exact_match(self):
        assert is_timezone_difference("2024:01:15 10:30:00", "2024:01:15 10:30:00") == False
    
    def test_one_hour_difference(self):
        assert is_timezone_difference("2024:01:15 11:30:00", "2024:01:15 10:30:00") == True
    
    def test_large_difference(self):
        assert is_timezone_difference("2024:01:16 10:30:00", "2024:01:15 10:30:00") == False
    
    def test_thirteen_hour_difference(self):
        assert is_timezone_difference("2024:01:15 23:30:00", "2024:01:15 10:30:00") == True
    
    def test_fourteen_hour_difference(self):
        assert is_timezone_difference("2024:01:16 00:30:00", "2024:01:15 10:30:00") == True


class TestAnalyzeDirectory:
    """Tests for analyze_directory function."""
    
    def test_analyze_returns_correct_structure(self, setup_test_data):
        stats = analyze_directory(TEST_DATA_DIR, progress=False)
        assert "total" in stats
        assert "correct" in stats
        assert "timezone_diff" in stats
        assert "need_update" in stats
        assert "no_json" in stats
    
    def test_analyze_counts_correctly(self, setup_test_data):
        stats = analyze_directory(TEST_DATA_DIR, progress=False)
        assert stats["total"] == 13
        assert len(stats["no_json"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])