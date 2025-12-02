#!/usr/bin/env python3
"""
Upload media files from local cache to S3.

This script:
1. Finds all post_media records without archive_url
2. Uploads corresponding files from local cache to S3
3. Updates archive_url field with S3 location
4. Uses date-based partitioning: s3://social-tui/cache/{YYYY}/{MM}/{filename}.{ext}

Usage:
    python upload_to_s3.py                    # Upload all unarchived media
    python upload_to_s3.py --limit 10         # Upload first 10 files
    python upload_to_s3.py --dry-run          # Show what would be uploaded
    python upload_to_s3.py --batch-size 50    # Upload 50 files at a time
    python upload_to_s3.py --force            # Re-upload even if archive_url exists
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from supabase_client import get_supabase_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_PROFILE = 'ab-power-user'
BUCKET_NAME = 'social-tui'
CACHE_ROOT = Path('cache/media')

# S3 key format: cache/{YYYY}/{MM}/{filename}.{ext}
def get_s3_key(local_path: Path, created_at: Optional[str] = None) -> str:
    """
    Generate S3 key with date-based partitioning.

    Args:
        local_path: Path to the local file
        created_at: ISO timestamp string (from post_media.created_at)

    Returns:
        S3 key in format: cache/{YYYY}/{MM}/{filename}.{ext}
    """
    filename = local_path.name

    # Use created_at timestamp if available, otherwise use file mtime
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Could not parse created_at '{created_at}': {e}, using file mtime")
            dt = datetime.fromtimestamp(local_path.stat().st_mtime)
    else:
        dt = datetime.fromtimestamp(local_path.stat().st_mtime)

    year = dt.strftime('%Y')
    month = dt.strftime('%m')

    return f"cache/{year}/{month}/{filename}"


def get_s3_client(profile_name: str = AWS_PROFILE):
    """
    Create S3 client using specified AWS profile.

    Args:
        profile_name: AWS profile name to use

    Returns:
        boto3 S3 client

    Raises:
        NoCredentialsError: If AWS credentials are not configured
    """
    try:
        session = boto3.Session(profile_name=profile_name)
        return session.client('s3')
    except Exception as e:
        logger.error(f"Failed to create S3 client with profile '{profile_name}': {e}")
        raise


def upload_file_to_s3(
    s3_client,
    local_path: Path,
    bucket: str,
    s3_key: str,
    mime_type: Optional[str] = None
) -> bool:
    """
    Upload a file to S3.

    Args:
        s3_client: boto3 S3 client
        local_path: Path to local file
        bucket: S3 bucket name
        s3_key: S3 key (path) for the file
        mime_type: Optional MIME type for Content-Type header

    Returns:
        True if upload successful, False otherwise
    """
    try:
        extra_args = {}
        if mime_type:
            extra_args['ContentType'] = mime_type

        logger.debug(f"Uploading {local_path} to s3://{bucket}/{s3_key}")
        s3_client.upload_file(
            str(local_path),
            bucket,
            s3_key,
            ExtraArgs=extra_args if extra_args else None
        )
        logger.info(f"✓ Uploaded to s3://{bucket}/{s3_key}")
        return True

    except FileNotFoundError:
        logger.error(f"✗ Local file not found: {local_path}")
        return False
    except ClientError as e:
        logger.error(f"✗ S3 upload error for {s3_key}: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error uploading {local_path}: {e}")
        return False


def get_media_to_upload(
    client,
    limit: Optional[int] = None,
    force: bool = False
) -> List[Dict]:
    """
    Get media records that need to be uploaded to S3.

    Args:
        client: Supabase client
        limit: Optional limit on number of records to return
        force: If True, include records that already have archive_url

    Returns:
        List of media record dictionaries
    """
    logger.info("Querying post_media for files to upload...")

    # Build query
    query = client.table('post_media').select(
        'media_id, media_type, local_file_path, mime_type, archive_url, created_at, md5_sum'
    )

    # Filter by archive_url unless force is True
    if not force:
        query = query.is_('archive_url', 'null')

    # Order by created_at (oldest first for backfill)
    query = query.order('created_at', desc=False)

    # Add limit if specified
    if limit:
        query = query.limit(limit)

    result = query.execute()
    media_records = result.data

    logger.info(f"Found {len(media_records)} media records to process")
    return media_records


def verify_local_file(media_record: Dict) -> Optional[Path]:
    """
    Verify that the local file exists for a media record.

    Tries multiple strategies to find the file:
    1. Use local_file_path from database if it exists
    2. Use md5_sum + extension derived from mime_type
    3. Search for md5_sum with any extension in the appropriate media type directory

    Args:
        media_record: Media record from database

    Returns:
        Path to local file if it exists, None otherwise
    """
    media_id = media_record['media_id']
    local_path_str = media_record.get('local_file_path')
    md5_sum = media_record.get('md5_sum')
    mime_type = media_record.get('mime_type')
    media_type = media_record.get('media_type', 'image')

    # Strategy 1: Try the path from database
    if local_path_str:
        local_path = Path(local_path_str)
        if local_path.exists():
            return local_path

    # Strategy 2: Use md5_sum + extension from mime_type
    if md5_sum and mime_type:
        # Get extension from MIME type
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/webm': '.webm',
            'video/quicktime': '.mov',
            'application/pdf': '.pdf',
        }
        ext = mime_to_ext.get(mime_type.lower(), '.bin')

        # Construct path based on media type
        media_dir = CACHE_ROOT / f"{media_type}s"  # images, videos, documents
        expected_path = media_dir / f"{md5_sum}{ext}"

        if expected_path.exists():
            logger.debug(f"Found file using md5_sum: {expected_path}")
            return expected_path

    # Strategy 3: Search for any file with matching md5_sum in the media type directory
    if md5_sum:
        media_dir = CACHE_ROOT / f"{media_type}s"
        if media_dir.exists():
            for file_path in media_dir.glob(f"{md5_sum}.*"):
                logger.debug(f"Found file by glob search: {file_path}")
                return file_path

    logger.warning(f"Media {media_id} not found (md5: {md5_sum}, path: {local_path_str})")
    return None


def update_archive_url(client, media_id: str, s3_url: str) -> bool:
    """
    Update the archive_url field in post_media table.

    Args:
        client: Supabase client
        media_id: Media record ID
        s3_url: S3 URL to store

    Returns:
        True if update successful, False otherwise
    """
    try:
        client.table('post_media').update({
            'archive_url': s3_url
        }).eq('media_id', media_id).execute()

        logger.debug(f"Updated archive_url for {media_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to update archive_url for {media_id}: {e}")
        return False


def upload_media_to_s3(
    dry_run: bool = False,
    limit: Optional[int] = None,
    batch_size: int = 50,
    force: bool = False
) -> Dict:
    """
    Main function to upload media files to S3.

    Args:
        dry_run: If True, only show what would be done
        limit: Optional limit on number of files to upload
        batch_size: Number of files to process in each batch
        force: If True, re-upload even if archive_url exists

    Returns:
        Dictionary with upload statistics
    """
    stats = {
        'total_media': 0,
        'files_found': 0,
        'files_missing': 0,
        'uploads_attempted': 0,
        'uploads_successful': 0,
        'uploads_failed': 0,
        'db_updates_successful': 0,
        'db_updates_failed': 0
    }

    # Get Supabase client
    client = get_supabase_client()

    # Get S3 client (skip if dry run)
    s3_client = None
    if not dry_run:
        try:
            s3_client = get_s3_client(AWS_PROFILE)
            logger.info(f"✓ Connected to S3 using profile '{AWS_PROFILE}'")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            return stats

    # Get media records to upload
    media_records = get_media_to_upload(client, limit=limit, force=force)
    stats['total_media'] = len(media_records)

    if not media_records:
        logger.info("No media files need uploading")
        return stats

    if dry_run:
        print("\n" + "=" * 80)
        print("DRY RUN - No files will be uploaded or database updated")
        print("=" * 80)
        print(f"\nWould process {len(media_records)} media files:\n")

        for i, record in enumerate(media_records[:20], 1):
            local_path = verify_local_file(record)
            status = "✓ Found" if local_path else "✗ Missing"

            if local_path:
                s3_key = get_s3_key(local_path, record.get('created_at'))
                s3_url = f"s3://{BUCKET_NAME}/{s3_key}"
                print(f"  {i}. [{status}] {record['media_id']}")
                print(f"     Local:  {local_path}")
                print(f"     S3:     {s3_url}")
            else:
                print(f"  {i}. [{status}] {record['media_id']}")
                print(f"     Path:   {record.get('local_file_path', 'N/A')}")

        if len(media_records) > 20:
            print(f"\n  ... and {len(media_records) - 20} more files")

        return stats

    # Process media files in batches
    print("\n" + "=" * 80)
    print("Uploading Media to S3")
    print("=" * 80)
    print(f"Bucket:  s3://{BUCKET_NAME}")
    print(f"Profile: {AWS_PROFILE}")
    print(f"Files:   {len(media_records)}")
    print()

    for i in range(0, len(media_records), batch_size):
        batch = media_records[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(media_records) + batch_size - 1) // batch_size

        print(f"\nBatch {batch_num}/{total_batches} ({len(batch)} files)")
        print("-" * 80)

        for record in batch:
            media_id = record['media_id']

            # Verify local file exists
            local_path = verify_local_file(record)
            if not local_path:
                stats['files_missing'] += 1
                print(f"  ✗ {media_id}: Local file not found")
                continue

            stats['files_found'] += 1

            # Generate S3 key and URL
            s3_key = get_s3_key(local_path, record.get('created_at'))
            s3_url = f"s3://{BUCKET_NAME}/{s3_key}"

            # Upload to S3
            stats['uploads_attempted'] += 1
            if upload_file_to_s3(
                s3_client,
                local_path,
                BUCKET_NAME,
                s3_key,
                record.get('mime_type')
            ):
                stats['uploads_successful'] += 1

                # Update database with archive_url
                if update_archive_url(client, media_id, s3_url):
                    stats['db_updates_successful'] += 1
                    print(f"  ✓ {media_id}: {local_path.name} → {s3_key}")
                else:
                    stats['db_updates_failed'] += 1
                    print(f"  ⚠ {media_id}: Uploaded but DB update failed")
            else:
                stats['uploads_failed'] += 1

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload media files from local cache to S3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python upload_to_s3.py                    # Upload all unarchived media
  python upload_to_s3.py --limit 10         # Upload first 10 files
  python upload_to_s3.py --dry-run          # Show what would be uploaded
  python upload_to_s3.py --batch-size 50    # Upload 50 files at a time
  python upload_to_s3.py --force            # Re-upload even if already archived

AWS Configuration:
  Profile: {profile}
  Bucket:  s3://{bucket}
  Format:  s3://{bucket}/cache/{{YYYY}}/{{MM}}/{{filename}}.{{ext}}
        """.format(profile=AWS_PROFILE, bucket=BUCKET_NAME)
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without uploading or updating database'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of files to upload'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of files to process in each batch (default: 50)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Re-upload files even if archive_url already exists'
    )

    args = parser.parse_args()

    try:
        stats = upload_media_to_s3(
            dry_run=args.dry_run,
            limit=args.limit,
            batch_size=args.batch_size,
            force=args.force
        )

        # Print summary
        print("\n" + "=" * 80)
        print("Upload Summary")
        print("=" * 80)
        print(f"Total Media Records:  {stats['total_media']}")
        print(f"Local Files Found:    {stats['files_found']}")
        print(f"Local Files Missing:  {stats['files_missing']}")
        print(f"\nUploads:")
        print(f"  Attempted:          {stats['uploads_attempted']}")
        print(f"  Successful:         {stats['uploads_successful']}")
        print(f"  Failed:             {stats['uploads_failed']}")
        print(f"\nDatabase Updates:")
        print(f"  Successful:         {stats['db_updates_successful']}")
        print(f"  Failed:             {stats['db_updates_failed']}")
        print("=" * 80)

        if not args.dry_run:
            if stats['uploads_failed'] == 0 and stats['db_updates_failed'] == 0:
                print("✓ Upload completed successfully")
            else:
                print("⚠ Upload completed with errors")
        else:
            print("ℹ Dry run completed (no changes made)")

        # Return error code if there were failures
        if stats['uploads_failed'] > 0 or stats['db_updates_failed'] > 0:
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n\nUpload interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
