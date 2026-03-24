# Google Photos Takeout Metadata Fixer

A Python script to fix EXIF metadata in Google Photos Takeout exports using the accompanying JSON sidecar files.

## Why This Script?

Google Photos Takeout exports your photos and videos, but the EXIF metadata (dates, GPS, descriptions) is stored in separate JSON files rather than embedded in the images. When you move your photos to another platform or organize them by date, the metadata is lost or incorrect.

**In 2026, many people are reconsidering their data storage choices** - moving away from US-based cloud services to self-hosted or EU-based alternatives (Nextcloud, PhotoPrism, Immich, etc.). This script helps ensure your photo library retains its correct dates and locations when making that transition.

## Table of Contents

- [Quick Start](#quick-start)
- [Background](#background)
- [What This Script Does](#what-this-script-does)
- [How It Works](#how-it-works)
  - [JSON File Matching](#json-file-matching)
  - [Truncated Filename Handling](#truncated-filename-handling)
  - [Timezone Handling](#timezone-handling)
- [Differences From Other Projects](#differences-from-other-projects)
- [Installation](#installation)
- [Usage](#usage)
  - [Command Line Options](#command-line-options)
  - [Examples](#examples)
- [Supported File Types](#supported-file-types)
- [Acknowledgments](#acknowledgments)
- [License](#license)

## Quick Start

```bash
# 1. Download your Google Photos Takeout
#    - Go to https://takeout.google.com
#    - Select only "Photos" for faster export
#    - Download all zip files to a folder (e.g., ~/Downloads/takeout)

# 2. Unzip all files (install parallel if needed: sudo apt install parallel)
cd ~/Downloads/takeout
parallel unzip -q {} -d ~/Pictures/Takeout ::: *.zip

# 3. Get this script
cd ~/Pictures/Takeout
git clone https://github.com/demeesterroel/google-photos-takeout-metadata-fixer.git
cd google-photos-takeout-metadata-fixer

# 4. Install exiftool (required)
sudo apt install libimage-exiftool-perl  # Ubuntu/Debian
brew install exiftool                     # macOS

# 5. Preview changes (dry run)
python3 fix_metadata.py '../Takeout/Google Photos' --no-extract --dryrun

# 6. Show summary statistics
python3 fix_metadata.py '../Takeout/Google Photos' --no-extract --summary

# 7. Actually fix the metadata (uncomment to run)
# python3 fix_metadata.py '../Takeout/Google Photos' --no-extract
```

## Background

When you export your Google Photos using [Google Takeout](https://takeout.google.com/), you receive:

1. Your photo/video files (JPG, HEIC, MP4, etc.)
2. JSON sidecar files containing metadata Google Photos stored separately

The JSON files contain important information:
- **photoTakenTime**: When the photo was actually taken
- **geoData**: GPS coordinates where the photo was taken
- **description**: Photo descriptions/captions
- **title**: Original filename

However, this metadata is **not embedded** in the image files themselves. This causes problems:

- Photos sorted by date appear in the wrong order
- Location information is lost
- Descriptions don't transfer to new platforms
- File modification dates are incorrect

This script reads the JSON files and writes the metadata directly into the image/video files using ExifTool.

## What This Script Does

For each media file in your Takeout:

1. **Finds the matching JSON file** (handles various Google naming quirks)
2. **Extracts the embedded metadata** from the JSON
3. **Compares dates**: Updates EXIF dates only if they differ (or are missing)
4. **Compares GPS**: Writes GPS data only if EXIF has no GPS or coordinates differ
5. **Writes descriptions** if present
6. **Sets file modification time** to match the photo date when dates are updated

### Timestamp Handling

- **Dates match exactly**: No date update needed
- **Timezone difference** (1-14 hours): Preserves EXIF dates by default (local time vs UTC)
- **Dates differ significantly**: Updates EXIF with JSON dates
- **No EXIF date**: Writes JSON date to EXIF

Use `--force-tz` to overwrite timezone differences.

### GPS Handling

GPS coordinates are handled **separately** from timestamps:

- **GPS in JSON matches EXIF**: No change
- **GPS in JSON differs from EXIF**: Updates GPS (even if timezone difference)
- **GPS in JSON but not in EXIF**: Adds GPS coordinates
- **No GPS in JSON**: Preserves existing EXIF GPS

### Timezone Handling

Google stores timestamps in UTC in the JSON files, but your photos may have local time in EXIF. This script:

- **By default**: Preserves EXIF dates if they differ from JSON by timezone offset (1-14 hours)
- **With `--force-tz`**: Overwrites with JSON times regardless of timezone

Note: GPS updates are **independent** of timezone settings. If JSON has GPS data that differs from EXIF, GPS will be updated even when dates are preserved.

### Video Support

Videos (MP4, MOV, etc.) also get their metadata updated:
- TrackCreateDate / TrackModifyDate
- MediaCreateDate / MediaModifyDate

## How It Works

### JSON File Matching

Google Takeout has inconsistent JSON naming patterns. This script handles:

| Pattern | Example Image | JSON File(s) Matched |
|---------|--------------|----------------------|
| Standard | `IMG_001.jpg` | `IMG_001.jpg.json`, `IMG_001.json` |
| Supplemental | `IMG_001.jpg` | `IMG_001.jpg.supplemental-metadata.json` |
| Truncated | `LongFilename.jpg` | `LongFile.supplemental-met.json` (truncated) |
| Edited | `IMG_001-edited.jpg` | Uses original's JSON: `IMG_001.jpg.json` |
| Duplicate | `IMG_001(1).jpg` | `IMG_001.jpg(1).json` |
| Version | `IMG_001~2.jpg` | `IMG_001.jpg.json` or `IMG_001~2.jpg.json` |
| Portrait/Bokeh | `IMG_001_Bokeh.jpg` | `IMG_001_Bokeh.jpg.supplemental-m.json` |
| Original | `original_uuid_I.jpg` | `original_uuid_.json` |

### Truncated Filename Handling

Google truncates both image filenames and JSON filenames when they exceed a length limit (typically 46 characters). This creates complex matching scenarios:

**Example truncation patterns:**
```
Image:  IMG_20260101_131741_Bokeh.jpg
JSON:   IMG_20260101_131741_Bokeh.jpg.supplemental-met.json
        (truncated from "supplemental-metadata")

Image:  photo_5969693298504960822_y.jpg  
JSON:   photo_5969693298504960822_y.jpg.supplemental-m.json
```

This script uses prefix matching to find `.supplemental*.json` files regardless of truncation.

### Timezone Handling

| Scenario | EXIF | JSON | Default Behavior | With `--force-tz` |
|----------|------|------|------------------|-------------------|
| Exact match | `2026-01-01 12:00` | `2026-01-01 12:00` | Skip (no change) | Skip (no change) |
| Timezone diff | `2026-01-01 13:00` | `2026-01-01 12:00` | **Preserve EXIF** | Overwrite with JSON |
| No EXIF | *(empty)* | `2026-01-01 12:00` | Write JSON date | Write JSON date |
| Large diff | `2026-01-01 15:00` | `2026-01-01 12:00` | Write JSON date | Write JSON date |

Timezone differences (1-14 hours) are assumed to be local vs UTC time differences and preserved by default.

## Differences From Other Projects

This script is inspired by and builds upon:

- **[google-photos-exif](https://github.com/mattwilson1024/google-photos-exif)** by mattwilson1024
- **[google-photos-takeout-date-fixer](https://github.com/laurentlbm/google-photos-takeout-date-fixer)** by laurentlbm (fork of the above)

### What's Different

| Feature | This Script | Other Projects |
|---------|-------------|----------------|
| **In-place updates** | Yes (no copies) | Creates output directory |
| **Truncated filename matching** | Advanced prefix matching | Basic patterns only |
| **`~N` version files** | Yes | No |
| **`_Bokeh` portrait files** | Yes | No |
| **`original_<uuid>_I` files** | Yes | No |
| **Timezone preservation** | Yes (optional) | No |
| **Progress feedback** | Yes | Limited |
| **Batch EXIF reading** | Yes (faster) | Per-file calls |
| **Summary/Report modes** | Yes | No |
| **Dry run mode** | Yes | No |

### Key Improvements

1. **Speed**: Uses batch EXIF reads instead of calling exiftool once per file (10x faster on large libraries)

2. **Better Matching**: Handles edge cases that other scripts miss:
   - Truncated `.supplemental-metadata.json` files
   - Portrait/Bokeh mode files
   - Signal app downloads (`signal-*.jpg`)
   - Screenshots from other apps
   - Files with `-EDIT` variant suffix

3. **Timezone Awareness**: Recognizes that EXIF often contains local time while JSON has UTC, and preserves this by default

4. **Reporting**: `--summary` shows what would change without modifying files

## Installation

### Prerequisites

- **Python 3.9+** (uses modern type hints)
- **ExifTool** by Phil Harvey ([exiftool.org](https://exiftool.org/))
- **Pillow** (for running tests only)

```bash
# Ubuntu/Debian
sudo apt install libimage-exiftool-perl python3 python3-pil

# macOS
brew install exiftool python3 pillow

# Windows (via Chocolatey)
choco install exiftool python
pip install Pillow
```

### Download

```bash
git clone https://github.com/demeesterroel/google-photos-takeout-metadata-fixer.git
cd google-photos-takeout-metadata-fixer
```

Or download just [`fix_metadata.py`](fix_metadata.py) directly.

## Running Tests

```bash
cd tests
./run_tests.sh
# or
python3 -m pytest test_fix_metadata.py -v
```

Tests cover:
- Standard JSON matching
- Truncated supplemental-metadata patterns
- Edited file variants (`-edited`, `-EDIT`)
- Version files (`~2`, `~3`)
- Duplicate patterns (`(1)`, `(2)`)
- Bokeh/portrait files
- Original UUID files
- Timezone difference detection

## Usage

### Command Line Options

```
usage: fix_metadata.py [-h] [--no-extract] [-n] [-s] [-r [FILE]] [-f] path

positional arguments:
  path                  Directory containing extracted files or zip files

options:
  -h, --help            show this help message and exit
  --no-extract          Path is already extracted (skip zip extraction)
  -n, --dryrun          Preview changes without executing
  -s, --summary         Show summary statistics only
  -r FILE, --report FILE
                        Write detailed report to file (default: <folder>_report.txt)
  -f, --force-tz        Overwrite timezone differences
```

### Examples

```bash
# Preview what would change (dry run)
python3 fix_metadata.py '~/Takeout/Google Photos/Photos from 2024' --no-extract --dryrun

# Show summary of a folder
python3 fix_metadata.py '~/Takeout/Google Photos/Photos from 2024' --no-extract --summary

# Generate detailed report
python3 fix_metadata.py '~/Takeout/Google Photos/Photos from 2024' --no-extract --report

# Fix metadata (preserve timezone differences)
python3 fix_metadata.py '~/Takeout/Google Photos/Photos from 2024' --no-extract

# Fix metadata AND overwrite timezone differences
python3 fix_metadata.py '~/Takeout/Google Photos/Photos from 2024' --no-extract --force-tz

# Process directly from downloaded zip
python3 fix_metadata.py '~/Downloads/takeout-20240101.zip'
```

### Example Output

```
Scanning files...
Found 2189 media files
Reading EXIF data...
Analyzing files...
  Processing 100/2189...
  Processing 200/2189...
  ...

Summary for: Photos from 2024
==================================================
Correct (no changes needed):        512
Need date update only:              120
Need GPS update only:                45
Need both date and GPS:             289
Timezone diff, dates preserved:    1203
Timezone diff + GPS differs:         12
No JSON found:                        8
--------------------------------------------------
Total needing updates:              466
Total files:                       2189
```

### Report Output

```bash
python3 fix_metadata.py '~/Takeout/Google Photos/Photos from 2024' --no-extract --report my_report.txt
```

Creates a detailed report with:
- Summary statistics
- Files needing date updates
- Files needing GPS updates
- Files needing both date and GPS
- Timezone differences preserved
- Files with no matching JSON

## Supported File Types

| Images | Videos | Raw |
|--------|--------|-----|
| .jpg | .mp4 | .dng |
| .jpeg | .mov | .raw |
| .png | .avi | .cr2 |
| .gif | .mkv | .nef |
| .bmp | .mpg | |
| .heic | .mpeg | |
| .heif | .webm | |

## Troubleshooting

### "No JSON found for: filename.jpg"

Some files genuinely don't have JSON files in the Takeout:
- **Live Photos/Motion Photos**: The video component (`.MP4`) may not have its own JSON
- **Screenshots from certain apps**: May not have export metadata
- **Very old uploads**: May predate Google's metadata tracking

Options:
1. Check if a related file has JSON (e.g., `IMG_001.HEIC` if `IMG_001.MP4` is missing)
2. Accept that some files can't be fixed

### Files showing timezone differences

This is normal and often correct! Google stores UTC times, but your camera stored local time. The `--summary` output shows how many files have timezone differences.

- If your photos have correct local times in EXIF → don't use `--force-tz`
- If EXIF times are wrong or missing → use `--force-tz` to use JSON times

### Script runs slowly on large folders

The script uses batch EXIF reading which should be fast. If still slow:
- Check you're not running on network storage
- Ensure Python 3.9+ is being used
- Try running on smaller subfolders

## Data Privacy

This script runs **entirely locally** on your machine. No data is uploaded anywhere. Your photos remain private.

When considering alternatives like Google Photos, remember:
- Your photos are used to train AI models
- Location data creates detailed profiles
- Exporting doesn't guarantee you get everything back

Moving to self-hosted solutions (Immich, PhotoPrism, Nextcloud) gives you control back. This script helps make that transition successful.

## Acknowledgments

This script was inspired by:

- **[mattwilson1024/google-photos-exif](https://github.com/mattwilson1024/google-photos-exif)** - Original tool for fixing Google Takeout EXIF metadata
- **[laurentlbm/google-photos-takeout-date-fixer](https://github.com/laurentlbm/google-photos-takeout-date-fixer)** - Improved fork with additional features

Both projects provided excellent documentation of Google's quirky export format and naming conventions. This script builds on that knowledge with:
- More robust JSON file matching for edge cases
- Better performance through batch processing
- Timezone-aware date handling
- Comprehensive reporting tools

### Why Not a Fork?

This is a **new standalone project** rather than a fork of the above repositories, for several reasons:

| Reason | This Project | Original Projects |
|--------|--------------|-------------------|
| **Language** | Python 3.9+ | TypeScript/JavaScript |
| **Runtime** | Just Python + exiftool | Requires Node.js, npm |
| **File handling** | Modifies in-place | Copies to output directory |
| **Performance** | Batch EXIF reads (fast) | Per-file subprocess calls |
| **Timezone awareness** | Yes (preserves local time) | No |
| **Reporting** | Summary & report modes | Limited output |

**Key architectural differences:**

1. **In-place modification**: This script fixes files where they are; the originals create a parallel output directory structure. This is simpler but means you should backup first.

2. **Language choice**: Python is pre-installed on most Linux/macOS systems and familiar to many. The originals require Node.js setup and npm dependencies.

3. **Speed optimization**: Batch reading EXIF metadata is ~10x faster than calling exiftool once per file. Large photo libraries (10,000+ files) complete in seconds rather than minutes.

4. **Philosophy**: This script is deliberately simple - one Python file with minimal dependencies. The originals have a more complex build process.

Creating a separate repository allows this project to evolve independently while still crediting the foundational work. Users can choose based on their needs:
- **This script** if you want Python, in-place edits, speed, and timezone awareness
- **Original scripts** if you prefer Node.js and want copies organized into output directories

## Disclaimer

**This script has only been tested on the author's personal photo library: ~20,000 files spanning 10 years of Google Photos exports.**

While it handles many edge cases discovered in that library, your Takeout may contain different naming patterns or edge cases not yet covered.

**Recommendations:**
1. **Always backup your photos** before running this script
2. Run `--dryrun` first to preview changes
3. Test on a small folder before running on your entire library
4. Check the `--report` output to verify matches before committing

If you encounter edge cases not handled, please open an issue with:
- The filename pattern
- Expected JSON filename
- Whether the JSON file exists but wasn't matched

## Contributing

Contributions welcome! Particularly:
- Additional edge cases for JSON file matching
- Performance improvements
- Support for additional file formats

## License

MIT License - use freely for personal or commercial purposes.

---

*Made in 2025, a time when many are reconsidering where their personal data lives.*
