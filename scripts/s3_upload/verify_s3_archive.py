#!/usr/bin/env python3
"""
Verify S3 archive status and provide statistics.

This script:
1. Shows statistics on archived vs unarchived media
2. Optionally verifies that S3 files actually exist
3. Checks for orphaned records (no local file)

Usage:
    python verify_s3_archive.py                  # Show statistics
    python verify_s3_archive.py --verify-s3      # Verify S3 files exist
    python verify_s3_archive.py --check-local    # Check for missing local files
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict
import boto3
from botocore.exceptions import ClientError

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from supabase_client import get_supabase_client
from scripts.s3_upload.upload_to_s3 import AWS_PROFILE, BUCKET_NAME, verify_local_file

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_archive_stats(client) -> Dict:
    """
    Get statistics about archived vs unarchived media.

    Args:
        client: Supabase client

    Returns:
        Dictionary with statistics
    """
    stats = {
        'total': 0,
        'archived': 0,
        'not_archived': 0,
        'by_type': {}
    }

    # Get total count
    result = client.table('post_media').select('media_id', count='exact').execute()
    stats['total'] = result.count

    # Get archived count
    result = client.table('post_media').select(
        'media_id', count='exact'
    ).not_.is_('archive_url', 'null').execute()
    stats['archived'] = result.count

    # Calculate not archived
    stats['not_archived'] = stats['total'] - stats['archived']

    # Get counts by media type
    for media_type in ['image', 'video', 'document']:
        # Total for type
        result = client.table('post_media').select(
            'media_id', count='exact'
        ).eq('media_type', media_type).execute()
        total = result.count

        # Archived for type
        result = client.table('post_media').select(
            'media_id', count='exact'
        ).eq('media_type', media_type).not_.is_('archive_url', 'null').execute()
        archived = result.count

        stats['by_type'][media_type] = {
            'total': total,
            'archived': archived,
            'not_archived': total - archived
        }

    return stats


def verify_s3_files(client, limit: int = None) -> Dict:
    """
    Verify that S3 files actually exist for archived media.

    Args:
        client: Supabase client
        limit: Optional limit on number of files to check

    Returns:
        Dictionary with verification results
    """
    results = {
        'checked': 0,
        'exists': 0,
        'missing': 0,
        'errors': 0,
        'missing_urls': []
    }

    # Get S3 client
    try:
        session = boto3.Session(profile_name=AWS_PROFILE)
        s3_client = session.client('s3')
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        return results

    # Get archived media records
    query = client.table('post_media').select(
        'media_id, archive_url'
    ).not_.is_('archive_url', 'null')

    if limit:
        query = query.limit(limit)

    media_records = query.execute().data

    print(f"\nVerifying {len(media_records)} S3 files...")
    print("-" * 80)

    for record in media_records:
        results['checked'] += 1
        archive_url = record['archive_url']

        # Parse S3 URL: s3://bucket/key
        if not archive_url.startswith('s3://'):
            logger.warning(f"Invalid S3 URL: {archive_url}")
            results['errors'] += 1
            continue

        # Extract bucket and key
        parts = archive_url[5:].split('/', 1)
        if len(parts) != 2:
            logger.warning(f"Invalid S3 URL format: {archive_url}")
            results['errors'] += 1
            continue

        bucket, key = parts

        # Check if object exists
        try:
            s3_client.head_object(Bucket=bucket, Key=key)
            results['exists'] += 1
            if results['checked'] % 10 == 0:
                print(f"  ✓ Checked {results['checked']} files...")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                results['missing'] += 1
                results['missing_urls'].append(archive_url)
                print(f"  ✗ Missing: {key}")
            else:
                results['errors'] += 1
                logger.error(f"Error checking {key}: {e}")

    return results


def check_local_files(client, limit: int = None) -> Dict:
    """
    Check for media records where local files are missing.

    Args:
        client: Supabase client
        limit: Optional limit on number of records to check

    Returns:
        Dictionary with results
    """
    results = {
        'checked': 0,
        'found': 0,
        'missing': 0,
        'missing_records': []
    }

    # Get all media records
    query = client.table('post_media').select(
        'media_id, media_type, local_file_path, mime_type, md5_sum'
    )

    if limit:
        query = query.limit(limit)

    media_records = query.execute().data

    print(f"\nChecking {len(media_records)} local files...")
    print("-" * 80)

    for record in media_records:
        results['checked'] += 1

        if verify_local_file(record):
            results['found'] += 1
        else:
            results['missing'] += 1
            results['missing_records'].append({
                'media_id': record['media_id'],
                'md5_sum': record.get('md5_sum'),
                'local_path': record.get('local_file_path')
            })

        if results['checked'] % 100 == 0:
            print(f"  Checked {results['checked']} files...")

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify S3 archive status and provide statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--verify-s3',
        action='store_true',
        help='Verify that S3 files actually exist'
    )
    parser.add_argument(
        '--check-local',
        action='store_true',
        help='Check for missing local files'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of files to check (for --verify-s3 and --check-local)'
    )

    args = parser.parse_args()

    client = get_supabase_client()

    # Get and display statistics
    print("\n" + "=" * 80)
    print("S3 Archive Statistics")
    print("=" * 80)

    stats = get_archive_stats(client)

    print(f"\nOverall:")
    print(f"  Total Media:       {stats['total']:,}")
    print(f"  Archived:          {stats['archived']:,} ({stats['archived']/stats['total']*100:.1f}%)" if stats['total'] > 0 else "  Archived:          0")
    print(f"  Not Archived:      {stats['not_archived']:,}")

    print(f"\nBy Type:")
    for media_type, type_stats in stats['by_type'].items():
        if type_stats['total'] > 0:
            pct = type_stats['archived'] / type_stats['total'] * 100
            print(f"  {media_type.capitalize()}:")
            print(f"    Total:           {type_stats['total']:,}")
            print(f"    Archived:        {type_stats['archived']:,} ({pct:.1f}%)")
            print(f"    Not Archived:    {type_stats['not_archived']:,}")

    # Verify S3 files if requested
    if args.verify_s3:
        print("\n" + "=" * 80)
        print("S3 File Verification")
        print("=" * 80)

        verify_results = verify_s3_files(client, limit=args.limit)

        print(f"\nResults:")
        print(f"  Checked:           {verify_results['checked']:,}")
        print(f"  Exists:            {verify_results['exists']:,}")
        print(f"  Missing:           {verify_results['missing']:,}")
        print(f"  Errors:            {verify_results['errors']:,}")

        if verify_results['missing_urls']:
            print(f"\nMissing files:")
            for url in verify_results['missing_urls'][:10]:
                print(f"  - {url}")
            if len(verify_results['missing_urls']) > 10:
                print(f"  ... and {len(verify_results['missing_urls']) - 10} more")

    # Check local files if requested
    if args.check_local:
        print("\n" + "=" * 80)
        print("Local File Check")
        print("=" * 80)

        local_results = check_local_files(client, limit=args.limit)

        print(f"\nResults:")
        print(f"  Checked:           {local_results['checked']:,}")
        print(f"  Found:             {local_results['found']:,}")
        print(f"  Missing:           {local_results['missing']:,}")

        if local_results['missing_records']:
            print(f"\nMissing local files:")
            for rec in local_results['missing_records'][:10]:
                print(f"  - {rec['media_id']}: md5={rec['md5_sum']}, path={rec['local_path']}")
            if len(local_results['missing_records']) > 10:
                print(f"  ... and {len(local_results['missing_records']) - 10} more")

    print("\n" + "=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
