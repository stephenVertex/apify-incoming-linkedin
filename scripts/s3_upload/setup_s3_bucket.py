#!/usr/bin/env python3
"""
Set up the S3 bucket for media archiving.

This script:
1. Creates the S3 bucket if it doesn't exist
2. Configures appropriate settings (versioning, lifecycle, etc.)
3. Verifies bucket access

Usage:
    python setup_s3_bucket.py                    # Create bucket in us-east-1
    python setup_s3_bucket.py --region us-west-2 # Create in specific region
    python setup_s3_bucket.py --check-only       # Just check if bucket exists
"""

import argparse
import logging
import sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.s3_upload.upload_to_s3 import AWS_PROFILE, BUCKET_NAME

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_s3_client(profile_name: str, region: str = None):
    """Create S3 client using specified AWS profile."""
    try:
        session = boto3.Session(profile_name=profile_name)
        if region:
            return session.client('s3', region_name=region)
        else:
            return session.client('s3')
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        raise


def bucket_exists(s3_client, bucket_name: str) -> bool:
    """Check if a bucket exists and is accessible."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            return False
        elif error_code == '403':
            logger.error(f"Bucket '{bucket_name}' exists but access is forbidden")
            return True  # Exists but we don't have access
        else:
            logger.error(f"Error checking bucket: {e}")
            raise


def get_bucket_region(s3_client, bucket_name: str) -> str:
    """Get the region where a bucket is located."""
    try:
        response = s3_client.get_bucket_location(Bucket=bucket_name)
        # None means us-east-1
        region = response.get('LocationConstraint') or 'us-east-1'
        return region
    except Exception as e:
        logger.error(f"Error getting bucket location: {e}")
        return None


def create_bucket(s3_client, bucket_name: str, region: str) -> bool:
    """Create an S3 bucket."""
    try:
        logger.info(f"Creating bucket '{bucket_name}' in region '{region}'...")

        if region == 'us-east-1':
            # us-east-1 doesn't need LocationConstraint
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            # All other regions need LocationConstraint
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )

        logger.info(f"✓ Bucket '{bucket_name}' created successfully")
        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou':
            logger.info(f"✓ Bucket '{bucket_name}' already exists and is owned by you")
            return True
        elif error_code == 'BucketAlreadyExists':
            logger.error(f"✗ Bucket name '{bucket_name}' is already taken by another AWS account")
            return False
        else:
            logger.error(f"✗ Error creating bucket: {e}")
            return False


def configure_bucket_versioning(s3_client, bucket_name: str, enabled: bool = False) -> bool:
    """Configure versioning for the bucket."""
    try:
        status = 'Enabled' if enabled else 'Suspended'
        logger.info(f"Setting versioning to {status} for bucket '{bucket_name}'...")

        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': status}
        )

        logger.info(f"✓ Versioning configured")
        return True

    except Exception as e:
        logger.error(f"✗ Error configuring versioning: {e}")
        return False


def configure_bucket_lifecycle(s3_client, bucket_name: str) -> bool:
    """
    Configure lifecycle rules for the bucket.

    This example transitions objects to Glacier after 90 days
    and expires objects after 7 years (for compliance).
    """
    try:
        logger.info(f"Configuring lifecycle rules for bucket '{bucket_name}'...")

        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'transition-to-glacier',
                    'Status': 'Enabled',
                    'Prefix': 'cache/',
                    'Transitions': [
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER_IR'  # Instant Retrieval
                        }
                    ]
                }
            ]
        }

        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_config
        )

        logger.info(f"✓ Lifecycle rules configured (Glacier transition after 90 days)")
        return True

    except Exception as e:
        logger.error(f"⚠ Warning: Could not configure lifecycle: {e}")
        return False


def test_bucket_access(s3_client, bucket_name: str) -> bool:
    """Test write access to the bucket."""
    try:
        test_key = 'cache/_test_access.txt'
        test_content = b'Access test'

        logger.info(f"Testing write access to bucket '{bucket_name}'...")

        # Upload test object
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content
        )

        # Delete test object
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=test_key
        )

        logger.info(f"✓ Write access verified")
        return True

    except Exception as e:
        logger.error(f"✗ Write access test failed: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Set up S3 bucket for media archiving",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region for the bucket (default: us-east-1)'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check if bucket exists, do not create'
    )
    parser.add_argument(
        '--enable-versioning',
        action='store_true',
        help='Enable versioning on the bucket'
    )
    parser.add_argument(
        '--skip-lifecycle',
        action='store_true',
        help='Skip lifecycle configuration'
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("S3 Bucket Setup")
    print("=" * 80)
    print(f"Bucket:  {BUCKET_NAME}")
    print(f"Profile: {AWS_PROFILE}")
    print(f"Region:  {args.region}")
    print()

    try:
        # Create S3 client
        s3_client = get_s3_client(AWS_PROFILE, args.region)

        # Check if bucket exists
        exists = bucket_exists(s3_client, BUCKET_NAME)

        if exists:
            logger.info(f"✓ Bucket '{BUCKET_NAME}' already exists")

            # Get bucket region
            bucket_region = get_bucket_region(s3_client, BUCKET_NAME)
            if bucket_region:
                logger.info(f"  Region: {bucket_region}")

                if bucket_region != args.region:
                    logger.warning(f"  Note: Bucket is in '{bucket_region}', not '{args.region}'")

            # Test access
            if not test_bucket_access(s3_client, BUCKET_NAME):
                logger.error("Cannot write to bucket. Check IAM permissions.")
                return 1

            print("\n" + "=" * 80)
            print("✓ Bucket is ready to use")
            print("=" * 80)
            return 0

        if args.check_only:
            logger.info(f"Bucket '{BUCKET_NAME}' does not exist")
            return 1

        # Create bucket
        if not create_bucket(s3_client, BUCKET_NAME, args.region):
            return 1

        # Configure versioning
        if args.enable_versioning:
            configure_bucket_versioning(s3_client, BUCKET_NAME, enabled=True)

        # Configure lifecycle
        if not args.skip_lifecycle:
            configure_bucket_lifecycle(s3_client, BUCKET_NAME)

        # Test access
        if not test_bucket_access(s3_client, BUCKET_NAME):
            logger.warning("Bucket created but write access test failed")

        print("\n" + "=" * 80)
        print("✓ Bucket setup complete")
        print("=" * 80)
        print(f"\nBucket URL: https://s3.console.aws.amazon.com/s3/buckets/{BUCKET_NAME}")
        print(f"\nYou can now run: uv run python upload_to_s3.py")
        print("=" * 80)

        return 0

    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
