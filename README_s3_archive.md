# S3 Media Archive

This feature uploads media files from the local cache to S3 for permanent archiving and updates the `archive_url` field in the `post_media` table.

## Overview

The S3 archive system:
- Uploads media from `cache/media/{images|videos|documents}/` to S3
- Uses date-based partitioning: `s3://social-tui/cache/{YYYY}/{MM}/{filename}.{ext}`
- Maintains original MD5-based filenames for consistency
- Updates the `archive_url` field in the `post_media` table
- Supports batch processing with progress tracking

## AWS Configuration

**AWS Profile**: `ab-power-user`
**Bucket**: `s3://social-tui`
**Path Format**: `s3://social-tui/cache/{YYYY}/{MM}/{filename}.{ext}`

The date partitioning uses the `created_at` timestamp from the `post_media` record. This ensures files are organized by when they were first cached.

## Scripts

All S3 archiving scripts are located in `scripts/s3_upload/`.

### 1. `setup_s3_bucket.py`

One-time setup script to create and configure the S3 bucket.

**Usage:**

```bash
# Create bucket in us-east-1 (default)
uv run python scripts/s3_upload/setup_s3_bucket.py

# Create bucket in a specific region
uv run python scripts/s3_upload/setup_s3_bucket.py --region us-west-2

# Just check if bucket exists
uv run python scripts/s3_upload/setup_s3_bucket.py --check-only

# Enable versioning
uv run python scripts/s3_upload/setup_s3_bucket.py --enable-versioning
```

**Features:**
- Creates the S3 bucket if it doesn't exist
- Configures lifecycle rules (transition to Glacier after 90 days)
- Tests write access
- Handles existing buckets gracefully

### 2. `upload_to_s3.py`

Main upload script that processes media files and uploads them to S3.

**Usage:**

```bash
# Upload all unarchived media
uv run python scripts/s3_upload/upload_to_s3.py

# Dry run (preview what would be uploaded)
uv run python scripts/s3_upload/upload_to_s3.py --dry-run

# Upload with limit
uv run python scripts/s3_upload/upload_to_s3.py --limit 100

# Custom batch size
uv run python scripts/s3_upload/upload_to_s3.py --batch-size 50

# Force re-upload of already archived files
uv run python scripts/s3_upload/upload_to_s3.py --force
```

**Features:**
- Automatically finds local files using MD5 checksums
- Handles mismatched file extensions (database has `.bin`, actual file has `.jpg`)
- Batch processing with progress indicators
- Updates database with S3 URLs after successful upload
- Comprehensive error handling and logging

**What it does:**
1. Queries `post_media` table for records where `archive_url IS NULL`
2. Locates corresponding local files in cache (using md5_sum + mime_type)
3. Uploads each file to S3 with date-based key
4. Updates `archive_url` field with S3 location (e.g., `s3://social-tui/cache/2025/12/abc123.jpg`)

### 3. `verify_s3_archive.py`

Verification and statistics script.

**Usage:**

```bash
# Show archive statistics
uv run python scripts/s3_upload/verify_s3_archive.py

# Verify S3 files actually exist
uv run python scripts/s3_upload/verify_s3_archive.py --verify-s3

# Check for missing local files
uv run python scripts/s3_upload/verify_s3_archive.py --check-local

# Limit verification checks
uv run python scripts/s3_upload/verify_s3_archive.py --verify-s3 --limit 100
```

**Features:**
- Shows total media count and archive status
- Breaks down statistics by media type (image, video, document)
- Optionally verifies S3 files exist using HEAD requests
- Checks for orphaned database records (no local file)

**Example Output:**

```
================================================================================
S3 Archive Statistics
================================================================================

Overall:
  Total Media:       1,082
  Archived:          0 (0.0%)
  Not Archived:      1,082

By Type:
  Image:
    Total:           946
    Archived:        0 (0.0%)
    Not Archived:    946
  Video:
    Total:           136
    Archived:        0 (0.0%)
    Not Archived:    136
================================================================================
```

## Database Schema

The `post_media` table includes:

```sql
CREATE TABLE post_media (
    media_id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    media_type TEXT NOT NULL,  -- 'image', 'video', 'document'
    media_url TEXT NOT NULL,   -- Original URL from social platform
    local_file_path TEXT,      -- Path to cached file
    md5_sum TEXT,              -- MD5 checksum of file content
    file_size INTEGER,
    mime_type TEXT,
    width INTEGER,
    height INTEGER,
    archive_url TEXT,          -- S3 URL (populated by upload script)
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_media_archive_url ON post_media(archive_url)
    WHERE archive_url IS NOT NULL;
```

## Workflow

### First-Time Setup

1. **Create the S3 bucket:**
   ```bash
   uv run python scripts/s3_upload/setup_s3_bucket.py
   ```

   This will:
   - Create the `social-tui` bucket in `us-east-1`
   - Configure lifecycle rules (transition to Glacier after 90 days)
   - Verify write access

   You only need to do this once.

### Initial Upload

1. **Check status:**
   ```bash
   uv run python scripts/s3_upload/verify_s3_archive.py
   ```

2. **Test with dry run:**
   ```bash
   uv run python scripts/s3_upload/upload_to_s3.py --dry-run --limit 10
   ```

3. **Upload a small batch:**
   ```bash
   uv run python scripts/s3_upload/upload_to_s3.py --limit 10
   ```

4. **Verify uploads:**
   ```bash
   # Check statistics
   uv run python scripts/s3_upload/verify_s3_archive.py

   # Or verify S3 files exist
   uv run python scripts/s3_upload/verify_s3_archive.py --verify-s3 --limit 10

   # Or check with AWS CLI
   aws s3 ls s3://social-tui/cache/2025/12/ --profile ab-power-user
   ```

5. **Upload all remaining:**
   ```bash
   uv run python scripts/s3_upload/upload_to_s3.py
   ```

### Backfilling New Media

After running `backfill_media.py` to download new media files:

```bash
# Upload newly cached media
uv run python scripts/s3_upload/upload_to_s3.py

# Check status
uv run python scripts/s3_upload/verify_s3_archive.py
```

## Error Handling

The upload script handles several error scenarios:

### Missing Local Files
If a database record has no local file, the script:
1. Tries the `local_file_path` from database
2. Constructs path from `md5_sum` + `mime_type`
3. Searches for any file with matching `md5_sum` in the media type directory

If the file still can't be found, it logs a warning and continues with other files.

### S3 Upload Failures
Failed uploads are logged but don't stop the batch. The `archive_url` is only updated for successful uploads.

### AWS Credentials
If AWS credentials for profile `ab-power-user` are not configured:
```bash
aws configure --profile ab-power-user
```

## File Organization

### Local Cache
```
cache/media/
├── images/
│   ├── {md5}.jpg
│   ├── {md5}.png
│   └── {md5}.gif
├── videos/
│   ├── {md5}.mp4
│   └── {md5}.webm
└── documents/
    └── {md5}.pdf
```

### S3 Archive
```
s3://social-tui/
└── cache/
    ├── 2025/
    │   ├── 11/
    │   │   ├── {md5}.jpg
    │   │   └── {md5}.png
    │   └── 12/
    │       ├── {md5}.jpg
    │       └── {md5}.mp4
    └── 2024/
        └── 12/
            └── {md5}.jpg
```

## Performance Considerations

- **Batch Size**: Default is 50 files per batch. Adjust with `--batch-size` for faster/slower uploads
- **Parallel Uploads**: Currently sequential. Could be parallelized for better performance
- **Network**: Upload speed depends on your network connection and AWS region proximity
- **Database Updates**: Each upload triggers a database UPDATE. Batched updates could improve performance

## Monitoring Upload Progress

The script provides detailed progress output:

```
================================================================================
Uploading Media to S3
================================================================================
Bucket:  s3://social-tui
Profile: ab-power-user
Files:   1,082

Batch 1/22 (50 files)
--------------------------------------------------------------------------------
  ✓ med-d2faa463: b955dfd266dabf072f82ebcd73e0efc1.jpg → cache/2025/12/b955dfd266dabf072f82ebcd73e0efc1.jpg
  ✓ med-efc9443a: 628152a8ec2c5fc201e8fd3d79718115.jpg → cache/2025/12/628152a8ec2c5fc201e8fd3d79718115.jpg
  ...
```

## Future Enhancements

Potential improvements:
- Parallel uploads using thread/process pools
- Resume capability for interrupted uploads
- S3 lifecycle policies for cost optimization
- CloudFront CDN integration for faster access
- Automated cleanup of local files after successful archive
- Integration with media backfill workflow

## Troubleshooting

### "Local file not found" warnings
Check if the file exists with the correct MD5:
```bash
ls cache/media/images/{md5}.*
```

### AWS credentials errors
Verify profile configuration:
```bash
aws configure list --profile ab-power-user
aws s3 ls s3://social-tui/ --profile ab-power-user
```

### Database connection errors
Check `.env` file has correct Supabase credentials:
```bash
grep SUPABASE .env
```

### S3 permissions
Ensure the AWS profile has permissions for:
- `s3:PutObject` on `s3://social-tui/cache/*`
- `s3:HeadObject` for verification

## Related Documentation

- [Media Cache Quickstart](MEDIA_CACHE_QUICKSTART.md)
- [Media Import Quickstart](MEDIA_IMPORT_QUICKSTART.md)
- [Database Schema](specs/database.md)
- [Worktree Usage](README_worktree-usage.md)
