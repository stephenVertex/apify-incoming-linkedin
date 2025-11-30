#!/usr/bin/env python3
"""
Data management script for LinkedIn posts.
Handles ingestion of JSON files into a SQLite database with deduplication.

Now uses the new schema with AWS-style identifiers and time-series tracking.
"""

import sqlite3
import json
import glob
import argparse
import os
import socket
from pathlib import Path
from datetime import datetime

from db_utils import generate_aws_id, PREFIX_POST, PREFIX_DOWNLOAD, PREFIX_RUN

DB_PATH = "data/posts_v2.db"


def get_connection():
    """Get database connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_post_urn(post):
    """Extract the best URN from a post object."""
    urn = post.get('full_urn')
    if not urn and 'urn' in post:
        if isinstance(post['urn'], dict):
            urn = post['urn'].get('activity_urn') or post['urn'].get('ugcPost_urn')
        else:
            urn = post['urn']
    return urn


def create_download_run(conn, script_name="import", platform="linkedin"):
    """Create a new download run record.

    Args:
        conn: Database connection
        script_name: Name of the script/process doing the import
        platform: Social media platform

    Returns:
        run_id: The ID of the created run
    """
    cursor = conn.cursor()
    run_id = generate_aws_id(PREFIX_RUN)

    system_info = json.dumps({
        "hostname": socket.gethostname(),
        "platform": platform,
        "script": script_name,
    })

    cursor.execute("""
        INSERT INTO download_runs (
            run_id, started_at, status, script_name, platform, system_info, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        datetime.now().isoformat(),
        'running',
        script_name,
        platform,
        system_info,
        datetime.now().isoformat()
    ))

    conn.commit()
    return run_id


def complete_download_run(conn, run_id, stats, error_message=None):
    """Mark a download run as completed.

    Args:
        conn: Database connection
        run_id: The run ID to complete
        stats: Dictionary with stats (processed, new, duplicates, errors)
        error_message: Optional error message if run failed
    """
    cursor = conn.cursor()

    status = 'failed' if error_message or stats['errors'] > 0 else 'completed'

    cursor.execute("""
        UPDATE download_runs
        SET completed_at = ?,
            status = ?,
            posts_fetched = ?,
            posts_new = ?,
            posts_updated = ?,
            error_message = ?
        WHERE run_id = ?
    """, (
        datetime.now().isoformat(),
        status,
        stats.get('processed', 0),
        stats.get('new', 0),
        0,  # posts_updated - we don't update in this version
        error_message,
        run_id
    ))

    conn.commit()


def import_directory(conn, directory, run_id=None):
    """Import all JSON files from a directory.

    Args:
        conn: Database connection
        directory: Directory containing JSON files
        run_id: Optional download run ID (will create one if not provided)

    Returns:
        Dictionary with import statistics
    """
    files = glob.glob(f"{directory}/*.json")
    print(f"Scanning {len(files)} files in {directory}...")

    cursor = conn.cursor()

    # Create download run if not provided
    if run_id is None:
        run_id = create_download_run(conn, script_name="manage_data.py")
        print(f"Created download run: {run_id}")

    stats = {
        "processed": 0,
        "new": 0,
        "duplicates": 0,
        "errors": 0
    }

    for fpath in files:
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)

            if not isinstance(data, list):
                # Handle single object files if necessary
                if isinstance(data, dict):
                    data = [data]
                else:
                    continue

            for post in data:
                stats["processed"] += 1
                urn = get_post_urn(post)

                if not urn:
                    print(f"Warning: No URN found for post in {fpath}")
                    stats["errors"] += 1
                    continue

                # Check if post already exists
                cursor.execute("SELECT post_id FROM posts WHERE urn = ?", (urn,))
                existing = cursor.fetchone()

                if existing:
                    # Post exists - create a new data_download entry for time-series
                    post_id = existing[0]
                    stats["duplicates"] += 1
                else:
                    # New post - create post and data_download
                    post_id = generate_aws_id(PREFIX_POST)

                    # Extract metadata for columns
                    author = post.get('author', {})
                    username = author.get('username', '')
                    text = post.get('text', '')
                    posted_at = post.get('posted_at', {})
                    timestamp = posted_at.get('timestamp')
                    post_type = post.get('post_type', 'regular')
                    url = post.get('url')

                    try:
                        cursor.execute("""
                            INSERT INTO posts (
                                post_id, urn, full_urn, platform, posted_at_timestamp,
                                author_username, text_content, post_type, url, raw_json,
                                first_seen_at, is_read, is_marked, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            post_id,
                            urn,
                            post.get('full_urn'),
                            'linkedin',
                            timestamp,
                            username,
                            text,
                            post_type,
                            url,
                            json.dumps(post),
                            datetime.now().isoformat(),
                            0,  # is_read
                            0,  # is_marked
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))
                        stats["new"] += 1
                    except sqlite3.IntegrityError as e:
                        print(f"Error inserting post {urn}: {e}")
                        stats["errors"] += 1
                        continue

                # Create data_download entry (for both new and existing posts)
                download_id = generate_aws_id(PREFIX_DOWNLOAD)

                # Extract stats
                stats_data = post.get('stats', {})
                total_reactions = stats_data.get('total_reactions', 0)

                try:
                    cursor.execute("""
                        INSERT INTO data_downloads (
                            download_id, post_id, run_id, downloaded_at,
                            total_reactions, stats_json, raw_json, source_file_path, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        download_id,
                        post_id,
                        run_id,
                        datetime.now().isoformat(),
                        total_reactions,
                        json.dumps(stats_data),
                        json.dumps(post),
                        fpath,
                        datetime.now().isoformat()
                    ))
                except sqlite3.IntegrityError as e:
                    print(f"Error creating data_download for {urn}: {e}")
                    stats["errors"] += 1

        except Exception as e:
            print(f"Error processing {fpath}: {e}")
            stats["errors"] += 1

    conn.commit()
    return stats, run_id


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manage LinkedIn posts data")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import JSON files")
    import_parser.add_argument("directory", help="Directory containing JSON files")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")

    args = parser.parse_args()

    # Check if database exists
    if not Path(DB_PATH).exists():
        print(f"Error: Database not found: {DB_PATH}")
        print("Please run the migration script first: python migrate_database.py")
        return

    conn = get_connection()

    try:
        if args.command == "import":
            if os.path.isdir(args.directory):
                stats, run_id = import_directory(conn, args.directory)

                # Complete the download run
                complete_download_run(conn, run_id, stats)

                print("\nImport Summary:")
                print(f"Run ID:     {run_id}")
                print(f"Processed:  {stats['processed']}")
                print(f"New:        {stats['new']}")
                print(f"Duplicates: {stats['duplicates']}")
                print(f"Errors:     {stats['errors']}")
            else:
                print(f"Error: Directory not found: {args.directory}")

        elif args.command == "stats":
            cursor = conn.cursor()

            # Post stats
            cursor.execute("SELECT COUNT(*) FROM posts")
            total_posts = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM posts WHERE is_marked=1")
            marked = cursor.fetchone()[0]

            # Download stats
            cursor.execute("SELECT COUNT(*) FROM data_downloads")
            total_downloads = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM download_runs")
            total_runs = cursor.fetchone()[0]

            cursor.execute("""
                SELECT date(first_seen_at), COUNT(*)
                FROM posts
                GROUP BY date(first_seen_at)
                ORDER BY date(first_seen_at)
            """)

            print(f"\nDatabase Statistics:")
            print(f"Total Posts:     {total_posts}")
            print(f"Marked Posts:    {marked}")
            print(f"Data Downloads:  {total_downloads}")
            print(f"Download Runs:   {total_runs}")
            print(f"\nIngestion History:")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} posts")

        else:
            parser.print_help()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
