"""Tag management for social-tui profiles with AWS-style identifiers."""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any

from db_utils import generate_aws_id, PREFIX_TAG, PREFIX_PROFILE_TAG


class TagManager:
    """Manages tags and profile-tag relationships with AWS-style IDs."""

    # Default tag colors
    DEFAULT_COLORS = {
        "aws": "cyan",
        "ai": "magenta",
        "startup": "green",
        "finops": "yellow",
        "cloud": "blue",
        "ml": "red",
    }

    def __init__(self, db_path: str = "data/posts_v2.db"):
        """Initialize TagManager with database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_default_tags()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory and foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_default_tags(self):
        """Create default tags if they don't exist."""
        default_tags = ["aws", "ai", "startup"]

        for tag_name in default_tags:
            # Check if tag exists
            existing = self.get_tag_by_name(tag_name)
            if not existing:
                color = self.DEFAULT_COLORS.get(tag_name, "white")
                self.add_tag(tag_name, color)

    def add_tag(self, name: str, color: str = "cyan", description: str = None) -> str:
        """Add a new tag to the database.

        Args:
            name: Tag name (must be unique)
            color: Color for the tag (default: cyan)
            description: Optional description of the tag

        Returns:
            Tag ID of the newly created tag (AWS-style)

        Raises:
            sqlite3.IntegrityError: If tag name already exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Normalize tag name to lowercase
            name = name.lower().strip()
            tag_id = generate_aws_id(PREFIX_TAG)

            cursor.execute("""
                INSERT INTO tags (tag_id, name, description, color, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (tag_id, name, description, color, datetime.now().isoformat()))

            conn.commit()
            return tag_id
        finally:
            conn.close()

    def delete_tag(self, tag_id: str) -> bool:
        """Delete a tag from the database.

        This will also remove all profile-tag associations (CASCADE).

        Args:
            tag_id: ID of the tag to delete

        Returns:
            True if tag was deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM tags WHERE tag_id = ?", (tag_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
        finally:
            conn.close()

    def rename_tag(self, tag_id: str, new_name: str) -> bool:
        """Rename a tag.

        Args:
            tag_id: ID of the tag to rename
            new_name: New name for the tag

        Returns:
            True if tag was renamed, False if not found

        Raises:
            sqlite3.IntegrityError: If new name already exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Normalize tag name to lowercase
            new_name = new_name.lower().strip()

            cursor.execute("""
                UPDATE tags SET name = ? WHERE tag_id = ?
            """, (new_name, tag_id))

            updated = cursor.rowcount > 0
            conn.commit()
            return updated
        finally:
            conn.close()

    def update_tag_color(self, tag_id: str, color: str) -> bool:
        """Update tag color.

        Args:
            tag_id: ID of the tag
            color: New color for the tag

        Returns:
            True if tag was updated, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE tags SET color = ? WHERE tag_id = ?
            """, (color, tag_id))

            updated = cursor.rowcount > 0
            conn.commit()
            return updated
        finally:
            conn.close()

    def update_tag_description(self, tag_id: str, description: str) -> bool:
        """Update tag description.

        Args:
            tag_id: ID of the tag
            description: New description for the tag

        Returns:
            True if tag was updated, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE tags SET description = ? WHERE tag_id = ?
            """, (description, tag_id))

            updated = cursor.rowcount > 0
            conn.commit()
            return updated
        finally:
            conn.close()

    def get_tag_by_id(self, tag_id: str) -> Optional[Dict[str, Any]]:
        """Get a tag by ID.

        Args:
            tag_id: ID of the tag

        Returns:
            Tag dictionary or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM tags WHERE tag_id = ?", (tag_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_tag_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tag by name.

        Args:
            name: Name of the tag

        Returns:
            Tag dictionary or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Normalize tag name to lowercase
            name = name.lower().strip()

            cursor.execute("SELECT * FROM tags WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """Get all tags from the database.

        Returns:
            List of tag dictionaries, sorted by name
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM tags ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_tags_with_counts(self) -> List[Dict[str, Any]]:
        """Get all tags with usage counts.

        Returns:
            List of tag dictionaries with 'usage_count' field
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT t.*, COUNT(pt.profile_tag_id) as usage_count
                FROM tags t
                LEFT JOIN profile_tags pt ON t.tag_id = pt.tag_id
                GROUP BY t.tag_id
                ORDER BY t.name
            """)

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def tag_profile(self, profile_id: str, tag_id: str) -> bool:
        """Add a tag to a profile.

        Args:
            profile_id: ID of the profile
            tag_id: ID of the tag

        Returns:
            True if tag was added, False if already tagged or error

        Raises:
            sqlite3.IntegrityError: If the profile-tag combination already exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            profile_tag_id = generate_aws_id(PREFIX_PROFILE_TAG)

            cursor.execute("""
                INSERT INTO profile_tags (profile_tag_id, profile_id, tag_id, created_at)
                VALUES (?, ?, ?, ?)
            """, (profile_tag_id, profile_id, tag_id, datetime.now().isoformat()))

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Already tagged
            return False
        finally:
            conn.close()

    def untag_profile(self, profile_id: str, tag_id: str) -> bool:
        """Remove a tag from a profile.

        Args:
            profile_id: ID of the profile
            tag_id: ID of the tag

        Returns:
            True if tag was removed, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM profile_tags
                WHERE profile_id = ? AND tag_id = ?
            """, (profile_id, tag_id))

            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
        finally:
            conn.close()

    def get_profile_tags(self, profile_id: str) -> List[Dict[str, Any]]:
        """Get all tags for a specific profile.

        Args:
            profile_id: ID of the profile

        Returns:
            List of tag dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT t.*
                FROM tags t
                JOIN profile_tags pt ON t.tag_id = pt.tag_id
                WHERE pt.profile_id = ?
                ORDER BY t.name
            """, (profile_id,))

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_profile_tag_names(self, profile_id: str) -> List[str]:
        """Get tag names for a profile.

        Args:
            profile_id: ID of the profile

        Returns:
            List of tag names
        """
        tags = self.get_profile_tags(profile_id)
        return [tag['name'] for tag in tags]

    def set_profile_tags(self, profile_id: str, tag_ids: List[str]):
        """Set tags for a profile (replaces existing tags).

        Args:
            profile_id: ID of the profile
            tag_ids: List of tag IDs to assign
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Remove all existing tags
            cursor.execute("DELETE FROM profile_tags WHERE profile_id = ?", (profile_id,))

            # Add new tags
            for tag_id in tag_ids:
                profile_tag_id = generate_aws_id(PREFIX_PROFILE_TAG)
                cursor.execute("""
                    INSERT INTO profile_tags (profile_tag_id, profile_id, tag_id, created_at)
                    VALUES (?, ?, ?, ?)
                """, (profile_tag_id, profile_id, tag_id, datetime.now().isoformat()))

            conn.commit()
        finally:
            conn.close()

    def get_or_create_tag(self, name: str, color: str = "cyan", description: str = None) -> Dict[str, Any]:
        """Get a tag by name, or create it if it doesn't exist.

        Args:
            name: Tag name
            color: Color for the tag if creating new (default: cyan)
            description: Optional description if creating new

        Returns:
            Tag dictionary
        """
        # Try to get existing tag
        tag = self.get_tag_by_name(name)

        if not tag:
            # Create new tag
            tag_id = self.add_tag(name, color, description)
            tag = self.get_tag_by_id(tag_id)

        return tag

    def clear_profile_tags(self, profile_id: str):
        """Remove all tags from a profile.

        Args:
            profile_id: ID of the profile
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM profile_tags WHERE profile_id = ?", (profile_id,))
            conn.commit()
        finally:
            conn.close()

    def get_profiles_by_tag(self, tag_id: str) -> List[str]:
        """Get all profile IDs that have a specific tag.

        Args:
            tag_id: ID of the tag

        Returns:
            List of profile IDs
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT profile_id
                FROM profile_tags
                WHERE tag_id = ?
                ORDER BY created_at
            """, (tag_id,))

            return [row['profile_id'] for row in cursor.fetchall()]
        finally:
            conn.close()
