#!/usr/bin/env python3
"""Unit tests for fix_metadata.py"""
import subprocess
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from fix_metadata import (
    find_json_for_file,
    parse_timestamp,
    is_timezone_difference,
    analyze_directory,
    get_json_gps,
)

TEST_DATA_DIR = Path(__file__).parent / "test_data"


def ensure_test_data():
    """Ensure test data exists, create if needed."""
    if not TEST_DATA_DIR.exists():
        print("Test data not found, creating...")
        result = subprocess.run(
            [sys.executable, Path(__file__).parent / "create_test_data.py"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            pytest.fail(f"Failed to create test data: {result.stderr}")


def build_all_files_dict():
    """Build all_files dict like os.walk would (filename -> Path)."""
    ensure_test_data()
    all_files = {}
    for f in TEST_DATA_DIR.iterdir():
        all_files[f.name] = f
    return all_files


@pytest.fixture(scope="module")
def setup_test_data():
    """Ensure test data exists and return all_files dict."""
    return build_all_files_dict()


class TestFindJsonForFile:
    """Tests for find_json_for_file function."""
    
    def test_standard_match(self, setup_test_data):
        all_files = setup_test_data
        result = find_json_for_file(all_files["correct.jpg"], all_files)
        assert result is not None
        assert result.name == "correct.jpg.json"
    
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


class TestGetJsonGps:
    """Tests for get_json_gps function."""
    
    def test_gps_present(self, setup_test_data):
        ensure_test_data()
        result = get_json_gps(TEST_DATA_DIR / "need_gps.jpg.json")
        assert result is not None
        lat, lon = result
        assert abs(lat - 51.5074) < 0.0001
        assert abs(lon - (-0.1278)) < 0.0001
    
    def test_gps_absent(self, setup_test_data):
        ensure_test_data()
        result = get_json_gps(TEST_DATA_DIR / "correct.jpg.json")
        assert result is None
    
    def test_gps_both_zero(self, setup_test_data):
        ensure_test_data()
        result = get_json_gps(TEST_DATA_DIR / "timezone.jpg.json")
        assert result is None


class TestAnalyzeDirectory:
    """Tests for analyze_directory function."""
    
    def test_analyze_returns_correct_structure(self, setup_test_data):
        ensure_test_data()
        stats = analyze_directory(TEST_DATA_DIR, progress=False)
        assert "total" in stats
        assert "correct" in stats
        assert "timezone_preserved" in stats
        assert "need_date" in stats
        assert "need_gps" in stats
        assert "need_both" in stats
        assert "tz_gps_diff" in stats
        assert "no_json" in stats
    
    def test_analyze_counts_correctly(self, setup_test_data):
        ensure_test_data()
        stats = analyze_directory(TEST_DATA_DIR, progress=False)
        assert stats["total"] == 19
        assert len(stats["no_json"]) == 1
    
    def test_correct_file_has_no_updates(self, setup_test_data):
        ensure_test_data()
        stats = analyze_directory(TEST_DATA_DIR, progress=False)
        correct_names = [item[0] for item in stats["correct"]]
        assert "correct.jpg" in correct_names
    
    def test_need_date_detected(self, setup_test_data):
        ensure_test_data()
        stats = analyze_directory(TEST_DATA_DIR, progress=False)
        need_date_names = [item[0] for item in stats["need_date"]]
        assert "need_date.jpg" in need_date_names
        assert "wrong_date.jpg" in need_date_names
    
    def test_need_gps_detected(self, setup_test_data):
        ensure_test_data()
        stats = analyze_directory(TEST_DATA_DIR, progress=False)
        need_gps_names = [item[0] for item in stats["need_gps"]]
        assert "need_gps.jpg" in need_gps_names
    
    def test_gps_correct_not_in_need_lists(self, setup_test_data):
        ensure_test_data()
        stats = analyze_directory(TEST_DATA_DIR, progress=False)
        all_update_names = (
            [item[0] for item in stats["need_date"]] +
            [item[0] for item in stats["need_gps"]] +
            [item[0] for item in stats["need_both"]] +
            [item[0] for item in stats["tz_gps_diff"]]
        )
        assert "gps_correct.jpg" not in all_update_names
    
    def test_timezone_preserved_detected(self, setup_test_data):
        ensure_test_data()
        stats = analyze_directory(TEST_DATA_DIR, progress=False)
        tz_names = [item[0] for item in stats["timezone_preserved"]]
        assert "timezone.jpg" in tz_names
    
    def test_tz_gps_diff_detected(self, setup_test_data):
        ensure_test_data()
        stats = analyze_directory(TEST_DATA_DIR, progress=False)
        tz_gps_names = [item[0] for item in stats["tz_gps_diff"]]
        assert "tz_gps_diff.jpg" in tz_gps_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])