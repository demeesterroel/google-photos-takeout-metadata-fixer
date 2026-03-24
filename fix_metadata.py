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
        if stem.endswith(f'({i})'):
            base_stem = stem[:-len(f'({i})')]
            base_with_ext = f"{base_stem}{suffix}"
            dupe_json = f"{base_with_ext}({i}).json"
            if dupe_json in all_files:
                return all_files[dupe_json]
    
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
    return diff_mins > 0 and diff_mins <= 14 * 60

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

def get_all_exif_gps(directory: Path, media_files: list) -> dict:
    """Get GPS coordinates from EXIF for all media files. Returns dict of {filename: (lat, lon) or None}."""
    result = subprocess.run(
        ['exiftool', '-json', '-r', '-GPSLatitude', '-GPSLongitude', '-n', str(directory)],
        capture_output=True, text=True
    )
    
    gps_data = {}
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            for item in data:
                source_file = item.get('SourceFile', '')
                lat = item.get('GPSLatitude')
                lon = item.get('GPSLongitude')
                if source_file:
                    filename = Path(source_file).name
                    if lat is not None and lon is not None:
                        try:
                            gps_data[filename] = (float(lat), float(lon))
                        except (ValueError, TypeError):
                            gps_data[filename] = None
                    else:
                        gps_data[filename] = None
        except:
            pass
    return gps_data

def get_current_exif_gps(media_path: Path) -> tuple[float, float] | None:
    """Get GPS coordinates from EXIF. Returns (lat, lon) or None."""
    try:
        result = subprocess.run(
            ['exiftool', '-GPSLatitude', '-GPSLongitude', '-n', str(media_path)],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            lat = None
            lon = None
            for line in lines:
                if 'GPS Latitude' in line and ': ' in line:
                    try:
                        lat = float(line.split(': ')[-1].strip())
                    except:
                        pass
                elif 'GPS Longitude' in line and ': ' in line:
                    try:
                        lon = float(line.split(': ')[-1].strip())
                    except:
                        pass
            if lat is not None and lon is not None:
                return (lat, lon)
    except:
        pass
    return None

def update_metadata(media_path: Path, json_path: Path, dryrun: bool = False, force: bool = False) -> str:
    """Update EXIF metadata from JSON file. Returns status string."""
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
    
    geo = data.get('geoData', {})
    lat = geo.get('latitude', 0.0)
    lon = geo.get('longitude', 0.0)
    has_json_gps = lat != 0.0 or lon != 0.0
    
    current_gps = get_current_exif_gps(media_path)
    has_exif_gps = current_gps is not None
    
    gps_differs = False
    if has_json_gps and has_exif_gps:
        exif_lat, exif_lon = current_gps
        if abs(lat - exif_lat) > 0.0001 or abs(lon - exif_lon) > 0.0001:
            gps_differs = True
    elif has_json_gps and not has_exif_gps:
        gps_differs = True
    
    description = data.get('description')
    
    dates_match = current_date and current_date == json_date
    is_tz_diff = current_date and is_timezone_difference(current_date, json_date)
    
    if dates_match and not is_tz_diff and not gps_differs and not description:
        return 'skip'
    
    if is_tz_diff and not force and not gps_differs and not description:
        return 'timezone'
    
    needs_date_update = not current_date or (current_date != json_date and (not is_tz_diff or force))
    needs_gps_update = gps_differs
    
    if not needs_date_update and not needs_gps_update and not description:
        return 'skip'
    
    cmd = ['exiftool', '-overwrite_original']
    
    if needs_date_update:
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
    
    if needs_gps_update:
        cmd.extend([
            f'-GPSLatitude={lat}',
            f'-GPSLatitudeRef={"N" if lat >= 0 else "S"}',
            f'-GPSLongitude={lon}',
            f'-GPSLongitudeRef={"E" if lon >= 0 else "W"}',
        ])
    
    if description:
        desc = description.replace('"', '\\"')
        cmd.append(f'-Description={desc}')
    
    cmd.append(str(media_path))
    
    if dryrun:
        parts = []
        if needs_date_update:
            parts.append('dates')
        if needs_gps_update:
            parts.append('GPS')
        if description:
            parts.append('description')
        print(f"  Would update ({', '.join(parts)}): {media_path.name}")
    
    if dryrun:
        if needs_date_update and needs_gps_update:
            return 'both'
        elif needs_date_update:
            return 'date'
        elif needs_gps_update:
            return 'gps'
        return 'skip'
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  exiftool error: {result.stderr}")
        return 'error'
    
    if needs_date_update:
        mtime = int(timestamp)
        os.utime(media_path, (mtime, mtime))
    
    if needs_date_update and needs_gps_update:
        return 'both'
    elif needs_date_update:
        return 'date'
    elif needs_gps_update:
        return 'gps'
    return 'skip'

def get_json_gps(json_path: Path) -> tuple[float, float] | None:
    """Get GPS coordinates from JSON file. Returns (lat, lon) or None."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        geo = data.get('geoData', {})
        lat = geo.get('latitude', 0.0)
        lon = geo.get('longitude', 0.0)
        if lat != 0.0 or lon != 0.0:
            return (lat, lon)
    except:
        pass
    return None

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
        print("Reading EXIF data...")
    
    exif_dates = get_all_exif_dates(base_dir, media_files)
    exif_gps = get_all_exif_gps(base_dir, media_files)
    
    if progress:
        print("Analyzing files...")
    
    correct = []
    need_date = []
    need_gps = []
    need_both = []
    timezone_preserved = []
    tz_gps_diff = []
    no_json = []
    
    for i, media in enumerate(sorted(media_files)):
        if progress and (i + 1) % 100 == 0:
            print(f"  Processing {i + 1}/{len(media_files)}...")
        
        json_file = find_json_for_file(media, all_files)
        exif_date = exif_dates.get(media.name)
        exif_gps_val = exif_gps.get(media.name)
        
        if json_file:
            json_date = get_json_date(json_file)
            json_gps = get_json_gps(json_file)
            
            if json_date:
                has_json_gps = json_gps is not None
                has_exif_gps = exif_gps_val is not None
                
                gps_differs = False
                if has_json_gps and has_exif_gps:
                    json_lat, json_lon = json_gps
                    exif_lat, exif_lon = exif_gps_val
                    if abs(json_lat - exif_lat) > 0.0001 or abs(json_lon - exif_lon) > 0.0001:
                        gps_differs = True
                elif has_json_gps and not has_exif_gps:
                    gps_differs = True
                
                if not exif_date:
                    if gps_differs:
                        need_both.append((media.name, "No EXIF", json_date, json_gps))
                    else:
                        need_date.append((media.name, "No EXIF", json_date))
                elif exif_date == json_date:
                    if gps_differs:
                        need_gps.append((media.name, exif_date, json_gps, exif_gps_val))
                    else:
                        correct.append((media.name, exif_date))
                elif is_timezone_difference(exif_date, json_date):
                    if gps_differs:
                        tz_gps_diff.append((media.name, exif_date, json_date, json_gps, exif_gps_val))
                    else:
                        timezone_preserved.append((media.name, exif_date, json_date))
                else:
                    if gps_differs:
                        need_both.append((media.name, exif_date, json_date, json_gps))
                    else:
                        need_date.append((media.name, exif_date, json_date))
            else:
                need_date.append((media.name, exif_date or "No EXIF", "No date in JSON"))
        else:
            no_json.append((media.name, exif_date or "No EXIF"))
    
    return {
        'total': len(media_files),
        'correct': correct,
        'need_date': need_date,
        'need_gps': need_gps,
        'need_both': need_both,
        'timezone_preserved': timezone_preserved,
        'tz_gps_diff': tz_gps_diff,
        'no_json': no_json,
    }

def print_summary(base_dir: Path):
    """Print summary statistics."""
    stats = analyze_directory(base_dir, progress=True)
    
    total = stats['total']
    correct = len(stats['correct'])
    need_date = len(stats['need_date'])
    need_gps = len(stats['need_gps'])
    need_both = len(stats['need_both'])
    tz_preserved = len(stats['timezone_preserved'])
    tz_gps_diff = len(stats['tz_gps_diff'])
    no_json = len(stats['no_json'])
    
    print(f"\nSummary for: {base_dir.name}")
    print("=" * 50)
    print(f"Correct (no changes needed):        {correct:>5}")
    print(f"Need date update only:              {need_date:>5}")
    print(f"Need GPS update only:               {need_gps:>5}")
    print(f"Need both date and GPS:            {need_both:>5}")
    print(f"Timezone diff, dates preserved:     {tz_preserved:>5}")
    print(f"Timezone diff + GPS differs:        {tz_gps_diff:>5}")
    print(f"No JSON found:                      {no_json:>5}")
    print("-" * 50)
    total_needing_update = need_date + need_gps + need_both + tz_gps_diff
    print(f"Total needing updates:              {total_needing_update:>5}")
    print(f"Total files:                        {total:>5}")

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
        f.write("-" * 50 + "\n")
        f.write(f"Total files:                    {stats['total']:>5}\n")
        f.write(f"Correct (no changes):           {len(stats['correct']):>5}\n")
        f.write(f"Need date update:               {len(stats['need_date']):>5}\n")
        f.write(f"Need GPS update:                {len(stats['need_gps']):>5}\n")
        f.write(f"Need both date and GPS:         {len(stats['need_both']):>5}\n")
        f.write(f"Timezone preserved:            {len(stats['timezone_preserved']):>5}\n")
        f.write(f"Timezone + GPS diff:            {len(stats['tz_gps_diff']):>5}\n")
        f.write(f"No JSON:                        {len(stats['no_json']):>5}\n")
        total_updates = len(stats['need_date']) + len(stats['need_gps']) + len(stats['need_both']) + len(stats['tz_gps_diff'])
        f.write(f"{'-' * 50}\n")
        f.write(f"Total needing updates:          {total_updates:>5}\n\n")
        
        if stats['need_date']:
            f.write(f"FILES NEEDING DATE UPDATE ({len(stats['need_date'])})\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Filename':<50} {'EXIF Date':<20} {'JSON Date':<20}\n")
            f.write("-" * 80 + "\n")
            for item in stats['need_date']:
                name, exif_date, json_date = item[:3]
                f.write(f"{name:<50} {exif_date:<20} {json_date:<20}\n")
            f.write("\n")
        
        if stats['need_gps']:
            f.write(f"FILES NEEDING GPS UPDATE ({len(stats['need_gps'])})\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Filename':<50} {'EXIF GPS':<25} {'JSON GPS':<25}\n")
            f.write("-" * 80 + "\n")
            for item in stats['need_gps']:
                name, exif_date, json_gps, exif_gps = item
                exif_str = f"{exif_gps[0]:.4f}, {exif_gps[1]:.4f}" if exif_gps else "None"
                json_str = f"{json_gps[0]:.4f}, {json_gps[1]:.4f}" if json_gps else "None"
                f.write(f"{name:<50} {exif_str:<25} {json_str:<25}\n")
            f.write("\n")
        
        if stats['need_both']:
            f.write(f"FILES NEEDING DATE AND GPS UPDATE ({len(stats['need_both'])})\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Filename':<50} {'EXIF Date':<20} {'JSON Date':<20}\n")
            f.write("-" * 80 + "\n")
            for item in stats['need_both']:
                name, exif_date, json_date = item[:3]
                f.write(f"{name:<50} {exif_date:<20} {json_date:<20}\n")
            f.write("\n")
        
        if stats['tz_gps_diff']:
            f.write(f"TIMEZONE DIFF + GPS DIFFERS ({len(stats['tz_gps_diff'])})\n")
            f.write(f"(Dates will be preserved, GPS will be updated)\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Filename':<50} {'EXIF Date':<20}\n")
            f.write("-" * 80 + "\n")
            for item in stats['tz_gps_diff']:
                name, exif_date = item[0], item[1]
                f.write(f"{name:<50} {exif_date:<20}\n")
            f.write("\n")
        
        if stats['timezone_preserved']:
            f.write(f"TIMEZONE DIFFERENCES (PRESERVED) ({len(stats['timezone_preserved'])})\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Filename':<50} {'EXIF':<20} {'JSON':<20}\n")
            f.write("-" * 80 + "\n")
            for name, exif_date, json_date in stats['timezone_preserved']:
                f.write(f"{name:<50} {exif_date:<20} {json_date:<20}\n")
            f.write("\n")
        
        if stats['no_json']:
            f.write(f"FILES WITH NO JSON ({len(stats['no_json'])})\n")
            f.write("-" * 80 + "\n")
            for name, exif_date in stats['no_json']:
                f.write(f"{name:<50} {exif_date}\n")
            f.write("\n")
        
        if stats['correct']:
            f.write(f"FILES WITH CORRECT METADATA ({len(stats['correct'])})\n")
            f.write("-" * 80 + "\n")
            for name, exif_date in stats['correct'][:10]:
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
    
    updated_date = 0
    updated_gps = 0
    updated_both = 0
    skipped = 0
    tz_skip = 0
    errors = 0
    
    for media in media_files:
        json_file = find_json_for_file(media, all_files)
        if json_file:
            result = update_metadata(media, json_file, dryrun, force_tz)
            if result == 'skip':
                skipped += 1
            elif result == 'timezone':
                tz_skip += 1
            elif result == 'gps':
                updated_gps += 1
                if not dryrun:
                    print(f"GPS updated: {media.name}")
            elif result == 'date':
                updated_date += 1
                if not dryrun:
                    print(f"Date updated: {media.name}")
            elif result == 'both':
                updated_both += 1
                if not dryrun:
                    print(f"Updated: {media.name}")
            else:
                errors += 1
        else:
            skipped += 1
            print(f"  No JSON found for: {media.name}")
    
    msg = f"\nSummary: "
    if dryrun:
        msg = f"\nWould update: "
    parts = []
    if updated_date:
        parts.append(f"{updated_date} date")
    if updated_gps:
        parts.append(f"{updated_gps} GPS")
    if updated_both:
        parts.append(f"{updated_both} date+GPS")
    if tz_skip:
        parts.append(f"{tz_skip} timezone skip")
    if skipped:
        parts.append(f"{skipped} correct")
    if errors:
        parts.append(f"{errors} errors")
    
    if parts:
        msg += ", ".join(parts)
    else:
        msg += "no changes needed"
    
    total_updates = updated_date + updated_gps + updated_both
    if total_updates:
        msg += f"\nTotal files {'would be ' if dryrun else ''}updated: {total_updates}"
    
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