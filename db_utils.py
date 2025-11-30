"""Database utilities for social-tui."""

import secrets
import re
from typing import Optional


def generate_aws_id(prefix: str) -> str:
    """Generate an AWS-style identifier with the given prefix.

    Args:
        prefix: The prefix to use (e.g., 'p', 'prf', 'tag')

    Returns:
        A string in the format '{prefix}-{xxxxxxxx}' where x is a hex character

    Examples:
        >>> id = generate_aws_id('p')
        >>> assert re.match(r'p-[0-9a-f]{8}', id)
    """
    # Generate 8 random hex characters (4 bytes = 8 hex chars)
    random_hex = secrets.token_hex(4)
    return f"{prefix}-{random_hex}"


def validate_aws_id(id_str: str, expected_prefix: Optional[str] = None) -> bool:
    """Validate an AWS-style identifier.

    Args:
        id_str: The ID string to validate
        expected_prefix: Optional prefix to check for

    Returns:
        True if the ID is valid, False otherwise

    Examples:
        >>> validate_aws_id('p-a1b2c3d4')
        True
        >>> validate_aws_id('invalid')
        False
        >>> validate_aws_id('p-a1b2c3d4', expected_prefix='p')
        True
        >>> validate_aws_id('p-a1b2c3d4', expected_prefix='prf')
        False
    """
    if not isinstance(id_str, str):
        return False

    # Match pattern: prefix-xxxxxxxx where x is hex
    pattern = r'^([a-z]{1,3})-([0-9a-f]{8})$'
    match = re.match(pattern, id_str)

    if not match:
        return False

    if expected_prefix and match.group(1) != expected_prefix:
        return False

    return True


def extract_prefix(id_str: str) -> Optional[str]:
    """Extract the prefix from an AWS-style ID.

    Args:
        id_str: The ID string

    Returns:
        The prefix if valid, None otherwise

    Examples:
        >>> extract_prefix('p-a1b2c3d4')
        'p'
        >>> extract_prefix('prf-12345678')
        'prf'
        >>> extract_prefix('invalid')
        None
    """
    pattern = r'^([a-z]{1,3})-[0-9a-f]{8}$'
    match = re.match(pattern, id_str)
    return match.group(1) if match else None


# Prefix constants for easy reference
PREFIX_POST = 'p'
PREFIX_DOWNLOAD = 'dl'
PREFIX_RUN = 'run'
PREFIX_PROFILE = 'prf'
PREFIX_TAG = 'tag'
PREFIX_PROFILE_TAG = 'pft'
PREFIX_POST_TAG = 'ptg'
PREFIX_ACTION = 'act'
PREFIX_MEDIA = 'med'
