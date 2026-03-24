#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
import tempfile
import shutil

def find_json_for_file(media_file: Path, all_files: dict) -> Path | None:
    """Find the matching JSON file for a media file."""
    name = media_file.name
    stem = media_file.stem
    suffix = media_file.suffix.lower()
    
    def try_patterns(patterns):
        for pattern in patterns:
            if pattern in all_files:
                return all_files[pattern]
        return None
    
    def find_supplemental_json(base_name):
        for filename in all_files:
            if filename.startswith(f"{base_name}.supplemental") and filename.endswith(".json"):
                return all_files[filename]
            if filename == f"{base_name}.json":
                return all_files[filename]
        return None
    
    patterns = [
        f"{name}.json",
        f"{stem}.json",
    ]
    result = try_patterns(patterns)
    if result:
        return result
    
    result = find_supplemental_json(name)
    if result:
        return result
    
    for filename in all_files:
        if filename.startswith(f"{name}.") and filename.endswith(".json") and filename != f"{name}.json":
            if "supplemental" in filename or "supplement" in filename:
                return all_files[filename]
    
    if stem.lower().endswith('-edited'):
        orig_stem = stem[:-7] if stem.endswith('-edited') else stem[:-5]
        for js in [f"{orig_stem}{suffix}.json", f"{orig_stem}.json"]:
            if js in all_files:
                return all_files[js]
        result = find_supplemental_json(f"{orig_stem}{suffix}")
        if result:
            return result
    
    if stem.lower().endswith('-edit'):
        orig_stem = stem[:-5]
        for js in [f"{orig_stem}{suffix}.json", f"{orig_stem}.json"]:
            if js in all_files:
                return all_files[js]
        result = find_supplemental_json(f"{orig_stem}{suffix}")
        if result:
            return result
    
    if stem.lower().endswith('_i'):
        base = stem[:-2]
        for suffix_pattern in ['_', '-']:
            json_name = f"{base}{suffix_pattern}.json"
            if json_name in all_files:
                return all_files[json_name]
    
    if stem.lower().endswith('_i(1)') or stem.lower().endswith('_i(2)'):
        base = stem[:-4] if '(1)' in stem else stem[:-4]
        for suffix_pattern in ['_', '-']:
            json_name = f"{base}{suffix_pattern}.json"
            if json_name in all_files:
                return all_files[json_name]
    
    if '~' in stem:
        base = stem.rsplit('~', 1)[0]
        for base_name in [f"{base}{suffix}", f"{base}"]:
            result = find_supplemental_json(base_name)
            if result:
                return result
            for js in [f"{base_name}.json"]:
                if js in all_files:
                    return all_files[js]
    
    for i in range(1, 100):
        dupe_pattern1 = f"{stem}({i}){suffix}.json"
        dupe_pattern2 = f"{stem}({i}).json"
        if dupe_pattern1 in all_files:
            return all_files[dupe_pattern1]
        if dupe_pattern2 in all_files:
            return all_files[dupe_pattern2]
    
    for i in range(1, 100):
        dupe_json = f"{stem}{suffix}({i}).json"
        if dupe_json in all_files:
            return all_files[dupe_json]
    
    if len(stem) > 2:
        for filename in all_files:
            if filename.endswith('.json'):
                json_stem = filename[:-5]
                if json_stem == stem[:-1] or stem[:-1] == json_stem:
                    return all_files[filename]
                if len(stem) > 10 and json_stem[:10] == stem[:10]:
                    return all_files[filename]
    
    return None

def parse_timestamp(ts: str) -> str | None:
    """Convert Unix timestamp to EXIF format YYYY:MM:DD HH:MM:SS."""
    from datetime import datetime, timezone
    try:
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return dt.strftime("%Y:%m:%d %H:%M:%S")
    except:
        return None

def parse_exif_to_minutes(exif_date: str) -> int | None:
    """Parse EXIF date string to total minutes from epoch-ish reference."""
    try:
        parts = exif_date.split(' ')
        date_parts = parts[0].split(':')
        time_parts = parts[1].split(':')
        year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
        hour, minute, sec = int(time_parts[0]), int(time_parts[1]), int(time_parts[2])
        return year * 525600 + month * 43200 + day * 1440 + hour * 60 + minute
    except:
        return None

def is_timezone_difference(exif_date: str, json_date: str) -> bool:
    """Check if EXIF and JSON dates differ by a timezone offset (1-14 hours)."""
    exif_mins = parse_exif_to_minutes(exif_date)
    json_mins = parse_exif_to_minutes(json_date)
    if exif_mins is None or json_mins is None:
        return False
    diff_mins = abs(exif_mins - json_mins)
    return diff_mins <= 14 * 60

def get_current_exif_date(media_path: Path) -> str | None:
    """Get current DateTimeOriginal from file, return None if not found."""
    try:
        result = subprocess.run(
            ['exiftool', '-DateTimeOriginal', '-d', '%Y:%m:%d %H:%M:%S', str(media_path)],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            line = result.stdout.strip()
            if ': ' in line:
                return line.split(': ', 1)[-1]
    except:
        pass
    return None

def get_all_exif_dates(directory: Path, media_files: list) -> dict:
    """Get DateTimeOriginal for all media files in one batch call. Returns dict of {filename: date}."""
    result = subprocess.run(
        ['exiftool', '-json', '-r', '-DateTimeOriginal', '-d', '%Y:%m:%d %H:%M:%S', str(directory)],
        capture_output=True, text=True
    )
    
    dates = {}
    if result.returncode == 0:
        try:
            import json
            data = json.loads(result.stdout)
            for item in data:
                source_file = item.get('SourceFile', '')
                date = item.get('DateTimeOriginal')
                if source_file and date:
                    dates[Path(source_file).name] = date
        except:
            pass
    return dates

def update_metadata(media_path: Path, json_path: Path, dryrun: bool = False, force: bool = False) -> str:
    """Update EXIF metadata from JSON file. Returns 'updated', 'skip', 'timezone', or 'error'."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  Error reading JSON: {e}")
        return 'error'
    
    photo_time = data.get('photoTakenTime', {})
    timestamp = photo_time.get('timestamp')
    
    if not timestamp:
        return 'error'
    
    json_date = parse_timestamp(timestamp)
    if not json_date:
        return 'error'
    
    current_date = get_current_exif_date(media_path)
    
    if current_date and current_date == json_date:
        return 'skip'
    
    if current_date and is_timezone_difference(current_date, json_date) and not force:
        return 'timezone'
    
    geo = data.get('geoData', {})
    lat = geo.get('latitude', 0.0)
    lon = geo.get('longitude', 0.0)
    
    cmd = ['exiftool', '-overwrite_original']
    cmd.extend([
        '-DateTimeOriginal=' + json_date,
        '-CreateDate=' + json_date,
        '-ModifyDate=' + json_date,
    ])
    
    if media_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv', '.mpg', '.mpeg']:
        cmd.extend([
            '-TrackCreateDate=' + json_date,
            '-TrackModifyDate=' + json_date,
            '-MediaCreateDate=' + json_date,
            '-MediaModifyDate=' + json_date,
        ])
    
    if lat != 0.0 or lon != 0.0:
        cmd.extend([
            f'-GPSLatitude={lat}',
            f'-GPSLatitudeRef={"N" if lat >= 0 else "S"}',
            f'-GPSLongitude={lon}',
            f'-GPSLongitudeRef={"E" if lon >= 0 else "W"}',
        ])
    
    if data.get('description'):
        desc = data['description'].replace('"', '\\"')
        cmd.append(f'-Description={desc}')
    
    cmd.append(str(media_path))
    
    if dryrun:
        print(f"  Would run: {' '.join(cmd)}")
        return 'updated'
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  exiftool error: {result.stderr}")
        return 'error'
    
    mtime = int(timestamp)
    os.utime(media_path, (mtime, mtime))
    
    return 'updated'

def get_json_date(json_path: Path) -> str | None:
    """Get photoTakenTime from JSON file as EXIF format string."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        timestamp = data.get('photoTakenTime', {}).get('timestamp')
        if timestamp:
            return parse_timestamp(timestamp)
    except:
        pass
    return None

def analyze_directory(base_dir: Path, progress: bool = False):
    """Analyze all media files and return stats and details."""
    media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic', '.heif',
                       '.mp4', '.mov', '.avi', '.mkv', '.mpg', '.mpeg', '.webm',
                       '.dng', '.raw', '.cr2', '.nef'}
    
    all_files = {}
    media_files = []
    
    if progress:
        print("Scanning files...")
    
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            p = Path(root) / f
            all_files[f] = p
            if p.suffix.lower() in media_extensions:
                media_files.append(p)
    
    if progress:
        print(f"Found {len(media_files)} media files")
        print("Reading EXIF dates...")
    
    exif_dates = get_all_exif_dates(base_dir, media_files)
    
    if progress:
        print("Analyzing files...")
    
    correct = []
    timezone_diff = []
    need_update = []
    no_json = []
    
    for i, media in enumerate(sorted(media_files)):
        if progress and (i + 1) % 100 == 0:
            print(f"  Processing {i + 1}/{len(media_files)}...")
        
        json_file = find_json_for_file(media, all_files)
        exif_date = exif_dates.get(media.name)
        
        if json_file:
            json_date = get_json_date(json_file)
            if json_date:
                if not exif_date:
                    need_update.append((media.name, "No EXIF", json_date))
                elif exif_date == json_date:
                    correct.append((media.name, exif_date, json_date))
                elif is_timezone_difference(exif_date, json_date):
                    timezone_diff.append((media.name, exif_date, json_date))
                else:
                    need_update.append((media.name, exif_date, json_date))
            else:
                need_update.append((media.name, exif_date or "No EXIF", "No date in JSON"))
        else:
            no_json.append((media.name, exif_date or "No EXIF", "No JSON"))
    
    return {
        'total': len(media_files),
        'correct': correct,
        'timezone_diff': timezone_diff,
        'need_update': need_update,
        'no_json': no_json,
    }

def print_summary(base_dir: Path):
    """Print summary statistics."""
    stats = analyze_directory(base_dir, progress=True)
    
    total = stats['total']
    correct = len(stats['correct'])
    timezone_diff = len(stats['timezone_diff'])
    need_update = len(stats['need_update'])
    no_json = len(stats['no_json'])
    
    print(f"\nSummary for: {base_dir.name}")
    print("=" * 40)
    print(f"Files with correct EXIF:    {correct:>5}")
    print(f"Timezone differences:       {timezone_diff:>5}")
    print(f"Files needing update:       {need_update:>5}")
    print(f"Files with no JSON:         {no_json:>5}")
    print(f"{'-' * 40}")
    print(f"Total media files:          {total:>5}")

def write_report(base_dir: Path, output_file: str | None = None):
    """Write detailed report to file."""
    stats = analyze_directory(base_dir, progress=True)
    
    if output_file is None:
        output_file = f"{base_dir.name}_report.txt"
    
    with open(output_file, 'w') as f:
        f.write(f"Report for: {base_dir}\n")
        f.write(f"Generated: {os.popen('date').read().strip()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total files:           {stats['total']:>5}\n")
        f.write(f"Correct EXIF:          {len(stats['correct']):>5}\n")
        f.write(f"Timezone differences:  {len(stats['timezone_diff']):>5}\n")
        f.write(f"Need update:           {len(stats['need_update']):>5}\n")
        f.write(f"No JSON:               {len(stats['no_json']):>5}\n\n")
        
        if stats['timezone_diff']:
            f.write(f"TIMEZONE DIFFERENCES ({len(stats['timezone_diff'])})\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Filename':<50} {'EXIF':<20} {'JSON':<20}\n")
            f.write("-" * 80 + "\n")
            for name, exif_date, json_date in stats['timezone_diff']:
                f.write(f"{name:<50} {exif_date:<20} {json_date:<20}\n")
            f.write("\n")
        
        if stats['need_update']:
            f.write(f"FILES NEEDING UPDATE ({len(stats['need_update'])})\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Filename':<50} {'EXIF':<20} {'JSON':<20}\n")
            f.write("-" * 80 + "\n")
            for name, exif_date, json_date in stats['need_update']:
                f.write(f"{name:<50} {exif_date:<20} {json_date:<20}\n")
            f.write("\n")
        
        if stats['no_json']:
            f.write(f"FILES WITH NO JSON ({len(stats['no_json'])})\n")
            f.write("-" * 80 + "\n")
            for name, exif_date, _ in stats['no_json']:
                f.write(f"{name:<50} {exif_date}\n")
            f.write("\n")
        
        if stats['correct']:
            f.write(f"FILES WITH CORRECT EXIF ({len(stats['correct'])})\n")
            f.write("-" * 80 + "\n")
            for name, exif_date, json_date in stats['correct'][:10]:
                f.write(f"{name:<50} {exif_date}\n")
            if len(stats['correct']) > 10:
                f.write(f"... and {len(stats['correct']) - 10} more\n")
    
    print(f"Report written to: {output_file}")

def process_directory(base_dir: Path, dryrun: bool = False, force_tz: bool = False):
    """Process all media files in a directory."""
    media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic', '.heif',
                       '.mp4', '.mov', '.avi', '.mkv', '.mpg', '.mpeg', '.webm',
                       '.dng', '.raw', '.cr2', '.nef'}
    
    all_files = {}
    media_files = []
    
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            p = Path(root) / f
            all_files[f] = p
            if p.suffix.lower() in media_extensions:
                media_files.append(p)
    
    print(f"Found {len(media_files)} media files")
    
    updated = 0
    skipped = 0
    timezone_skipped = 0
    errors = 0
    
    for media in media_files:
        json_file = find_json_for_file(media, all_files)
        if json_file:
            result = update_metadata(media, json_file, dryrun, force_tz)
            if result == 'skip':
                skipped += 1
            elif result == 'timezone':
                timezone_skipped += 1
            elif result == 'updated':
                if not dryrun:
                    print(f"Updated: {media.name}")
                updated += 1
            else:
                errors += 1
        else:
            skipped += 1
            print(f"  No JSON found for: {media.name}")
    
    msg = f"\nDone: {updated} {'would be ' if dryrun else ''}updated"
    if timezone_skipped:
        msg += f", {timezone_skipped} timezone differences skipped"
    msg += f", {skipped} already correct, {errors} errors"
    print(msg)

def process_zip(zip_path: Path, extract_dir: Path, dryrun: bool = False, force_tz: bool = False):
    """Extract and process a single zip file."""
    print(f"\n=== Processing: {zip_path.name} ===")
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = zf.namelist()
        if not names:
            return
        
        zf.extractall(extract_dir)
    
    for item in extract_dir.iterdir():
        if item.is_dir():
            google_photos = item / "Google Photos"
            if google_photos.exists():
                process_directory(google_photos, dryrun, force_tz)
                return
            process_directory(item, dryrun, force_tz)
            return

def main():
    import argparse
    ap = argparse.ArgumentParser(
        description='Fix Google Takeout photo metadata from JSON files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s /path/to/Takeout --no-extract          # Process extracted folder
  %(prog)s /path/to/zips/                          # Process zip files
  %(prog)s /path/to/folder --summary               # Show summary only
  %(prog)s /path/to/folder --report                # Generate detailed report
  %(prog)s /path/to/folder --dryrun                # Preview changes
  %(prog)s /path/to/folder --force-tz              # Overwrite timezone differences

Timezone handling:
  By default, files with timezone differences (EXIF differs from JSON by 1-14 hours)
  are preserved (not updated). Use --force-tz to overwrite these with JSON times.
""")
    ap.add_argument('path', help='Directory containing extracted files or zip files')
    ap.add_argument('--no-extract', action='store_true', help='Path is already extracted (skip zip extraction)')
    ap.add_argument('-n', '--dryrun', action='store_true', help='Dry run - show what would be done without making changes')
    ap.add_argument('-s', '--summary', action='store_true', help='Print summary statistics only')
    ap.add_argument('-r', '--report', nargs='?', const='', metavar='FILE', help='Write detailed report to file (default: <folder>_report.txt)')
    ap.add_argument('-f', '--force-tz', action='store_true', help='Force overwrite timezone differences (default: preserve)')
    args = ap.parse_args()
    
    path = Path(args.path)
    
    if not path.exists():
        print(f"Error: {path} does not exist")
        sys.exit(1)
    
    if args.summary:
        print_summary(path)
        return
    
    if args.report is not None:
        output_file = args.report if args.report else None
        write_report(path, output_file)
        return
    
    if args.dryrun:
        print("*** DRY RUN - No changes will be made ***\n")
    
    if args.force_tz:
        print("*** FORCE TIMEZONE - Will overwrite timezone differences ***\n")
    
    if args.no_extract:
        process_directory(path, args.dryrun, args.force_tz)
    else:
        zips = list(path.glob("*.zip"))
        
        if zips:
            for zip_file in sorted(zips):
                with tempfile.TemporaryDirectory() as tmpdir:
                    process_zip(zip_file, Path(tmpdir), args.dryrun, args.force_tz)
        else:
            process_directory(path, args.dryrun, args.force_tz)

if __name__ == '__main__':
    main()