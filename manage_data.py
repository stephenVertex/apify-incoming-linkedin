#!/usr/bin/env python3
"""
Data management script for LinkedIn posts.
Handles ingestion of JSON files into a SQLite database with deduplication.
"""

import sqlite3
import json
import glob
import argparse
import os
from pathlib import Path
from datetime import datetime

DB_PATH = "data/posts.db"

def init_db():
    """Initialize the database schema."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS posts (
        urn TEXT PRIMARY KEY,
        full_urn TEXT,
        posted_at_timestamp INTEGER,
        author_username TEXT,
        text_content TEXT,
        json_data TEXT,
        source_file TEXT,
        first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        imported_at TIMESTAMP,
        is_read BOOLEAN DEFAULT 0,
        is_marked BOOLEAN DEFAULT 0
    )
    ''')
    
    # Add indices for common queries
    c.execute('CREATE INDEX IF NOT EXISTS idx_posted_at ON posts(posted_at_timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_first_seen ON posts(first_seen_at)')
    
    conn.commit()
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

def import_directory(conn, directory):
    """Import all JSON files from a directory."""
    files = glob.glob(f"{directory}/*.json")
    print(f"Scanning {len(files)} files in {directory}...")
    
    c = conn.cursor()
    imported_at = datetime.now().isoformat()
    
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
                # Handle single object files if necessary, though structure seems to be list
                if isinstance(data, dict):
                    data = [data]
                else:
                    continue
                    
            for post in data:
                stats["processed"] += 1
                urn = get_post_urn(post)
                
                if not urn:
                    print(f"Warning: No URN found for post in {fpath}")
                    continue
                
                # Extract some metadata for columns
                author = post.get('author', {})
                username = author.get('username', '')
                text = post.get('text', '')
                posted_at = post.get('posted_at', {})
                timestamp = posted_at.get('timestamp')
                
                try:
                    c.execute('''
                    INSERT INTO posts (
                        urn, full_urn, posted_at_timestamp, author_username, 
                        text_content, json_data, source_file, imported_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        urn,
                        post.get('full_urn'),
                        timestamp,
                        username,
                        text,
                        json.dumps(post),
                        fpath,
                        imported_at
                    ))
                    stats["new"] += 1
                except sqlite3.IntegrityError:
                    stats["duplicates"] += 1
                    
        except Exception as e:
            print(f"Error processing {fpath}: {e}")
            stats["errors"] += 1
            
    conn.commit()
    return stats

def main():
    parser = argparse.ArgumentParser(description="Manage LinkedIn posts data")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import JSON files")
    import_parser.add_argument("directory", help="Directory containing JSON files")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    
    args = parser.parse_args()
    
    conn = init_db()
    
    if args.command == "import":
        if os.path.isdir(args.directory):
            stats = import_directory(conn, args.directory)
            print("\nImport Summary:")
            print(f"Processed: {stats['processed']}")
            print(f"New:       {stats['new']}")
            print(f"Duplicates:{stats['duplicates']}")
            print(f"Errors:    {stats['errors']}")
        else:
            print(f"Error: Directory not found: {args.directory}")
            
    elif args.command == "stats":
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM posts")
        total = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM posts WHERE is_marked=1")
        marked = c.fetchone()[0]
        
        c.execute("SELECT date(first_seen_at), COUNT(*) FROM posts GROUP BY date(first_seen_at) ORDER BY date(first_seen_at)")
        print(f"\nTotal Posts: {total}")
        print(f"Marked Posts: {marked}")
        print("\nIngestion History:")
        for row in c.fetchall():
            print(f"  {row[0]}: {row[1]} posts")
            
    else:
        parser.print_help()
        
    conn.close()

if __name__ == "__main__":
    main()
