#!/usr/bin/env python3
"""
Rename .bin files to proper extensions based on their MIME type.
"""
from pathlib import Path
import subprocess

# Process both images and videos
cache_dirs = [
    Path("cache/media/images"),
    Path("cache/media/videos"),
    Path("cache/media/documents"),
]

total_renamed = 0

for cache_dir in cache_dirs:
    if not cache_dir.exists():
        continue

    # Get all .bin files
    bin_files = list(cache_dir.glob("*.bin"))
    if not bin_files:
        continue

    print(f"\n{cache_dir.name.upper()}:")
    print(f"Found {len(bin_files)} .bin files")

    renamed = 0
    for bin_file in bin_files:
        # Use 'file' command to detect type
        result = subprocess.run(
            ["file", "--mime-type", "-b", str(bin_file)],
            capture_output=True,
            text=True
        )
        mime_type = result.stdout.strip()

        # Map MIME type to extension
        ext_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'video/webm': '.webm',
            'application/pdf': '.pdf',
        }

        new_ext = ext_map.get(mime_type, '.bin')

        if new_ext != '.bin':
            new_name = bin_file.with_suffix(new_ext)
            bin_file.rename(new_name)
            renamed += 1
            if renamed <= 3:  # Show first 3 per directory
                print(f"  ✓ {bin_file.name} → {new_name.name} ({mime_type})")

    print(f"  Renamed {renamed} files")
    total_renamed += renamed

print(f"\n✓ Total renamed: {total_renamed} files")
