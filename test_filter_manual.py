#!/usr/bin/env python3
"""
Interactive testing script for content filter.
Loads real posts from database and tests filtering without the UI.
Uses RapidFuzz for fuzzy matching (same as implemented in interactive_posts.py).
"""

import sys
import json
from supabase_client import get_supabase_client
from rapidfuzz import fuzz

def create_searchable_text(post: dict) -> str:
    """
    Create searchable text from post fields.
    This should match the implementation in interactive_posts.py
    """
    parts = []

    # Extract text from post
    if 'text' in post:
        parts.append(post['text'])

    # Add author username for searching
    if 'author_username' in post:
        parts.append(post['author_username'])

    # Add author name if available
    if 'author' in post and isinstance(post['author'], dict):
        if 'name' in post['author']:
            parts.append(post['author']['name'])

    return ' '.join(parts).lower()

def load_posts_for_testing(limit: int = 100):
    """Load posts from database for testing."""
    print(f"Loading {limit} posts from database...")
    client = get_supabase_client()

    # Load from view
    result = client.table('v_main_post_view').select('*').limit(limit).execute()
    posts_data = result.data

    if not posts_data:
        print("No posts found in database!")
        return []

    # Get raw_json for full text
    post_ids = [row['post_id'] for row in posts_data]
    raw_json_result = client.table('posts').select('post_id, raw_json').in_('post_id', post_ids).execute()
    raw_json_map = {row['post_id']: row['raw_json'] for row in raw_json_result.data}

    # Combine data
    posts = []
    for row in posts_data:
        post = json.loads(raw_json_map.get(row['post_id'], '{}'))
        post['post_id'] = row['post_id']
        post['author_username'] = row['author_username']
        post['text_preview'] = row['text_preview']
        post['platform'] = row['platform']
        post['posted_at_formatted'] = row['posted_at_formatted']

        # Create the _searchable field for testing
        post['_searchable'] = create_searchable_text(post)

        posts.append(post)

    print(f"Loaded {len(posts)} posts")
    return posts

def test_filter(posts: list, filter_text: str, threshold: int = 80):
    """
    Test filtering with RapidFuzz fuzzy matching.

    Uses the same hybrid approach as interactive_posts.py:
    - Single word: partial_ratio for substring matching
    - Multi-word: ALL words must match with partial_ratio
    """
    if not filter_text:
        return posts  # Empty filter returns all

    filter_lower = filter_text.lower().strip()
    filter_words = filter_lower.split()
    matched = []

    for post in posts:
        searchable = post.get('_searchable', '')
        if not searchable:
            continue

        # Hybrid approach matching implementation
        filter_match = False

        if len(filter_words) == 1:
            # Single word query
            score = fuzz.partial_ratio(filter_lower, searchable)
            if score >= threshold:
                filter_match = True
        else:
            # Multi-word query: ALL words must match
            all_match = all(
                fuzz.partial_ratio(word, searchable) >= threshold
                for word in filter_words
            )
            if all_match:
                filter_match = True

        if filter_match:
            matched.append(post)

    return matched

def show_post_details(post: dict):
    """Show detailed information about a post."""
    print("\n" + "=" * 60)
    print(f"Post ID: {post.get('post_id')}")
    print(f"Author: @{post.get('author_username')}")
    print(f"Platform: {post.get('platform')}")
    print(f"Posted: {post.get('posted_at_formatted')}")
    print("-" * 60)

    # Show full text if available
    text = post.get('text', '')
    if text:
        print(f"Text: {text[:500]}")
        if len(text) > 500:
            print(f"... ({len(text) - 500} more characters)")
    else:
        print(f"Preview: {post.get('text_preview', '')}")

    print("-" * 60)
    print(f"Searchable text: {post.get('_searchable', '')[:200]}...")
    print("=" * 60)

def main():
    """Run interactive filter testing."""
    print("\n" + "=" * 60)
    print("Content Filter Tester - Loading posts...")
    print("=" * 60)

    try:
        posts = load_posts_for_testing(limit=100)
    except Exception as e:
        print(f"\n❌ Error loading posts: {e}")
        import traceback
        traceback.print_exc()
        return

    if not posts:
        print("No posts to test! Exiting.")
        return

    print(f"\n✅ Loaded {len(posts)} posts")
    print("\nCommands:")
    print("  - Type search terms to test filtering")
    print("  - Type 'show <number>' to see full details of a result")
    print("  - Type 'stats' to see database statistics")
    print("  - Type 'quit' or 'q' to exit")
    print("=" * 60)

    last_results = []

    while True:
        try:
            user_input = input("\n> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nExiting...")
                break

            # Show command
            if user_input.lower().startswith('show '):
                try:
                    index = int(user_input.split()[1]) - 1
                    if 0 <= index < len(last_results):
                        show_post_details(last_results[index])
                    else:
                        print(f"Invalid index. Use 1-{len(last_results)}")
                except (ValueError, IndexError):
                    print("Usage: show <number>")
                continue

            # Stats command
            if user_input.lower() == 'stats':
                print(f"\nDatabase Statistics:")
                print(f"  Total posts loaded: {len(posts)}")

                # Platform breakdown
                platforms = {}
                for post in posts:
                    platform = post.get('platform', 'unknown')
                    platforms[platform] = platforms.get(platform, 0) + 1

                print(f"  Platform breakdown:")
                for platform, count in sorted(platforms.items(), key=lambda x: -x[1]):
                    print(f"    - {platform}: {count}")

                continue

            # Filter test
            filter_text = user_input
            results = test_filter(posts, filter_text)
            last_results = results

            print(f"\n🔍 Filter: '{filter_text}'")
            print(f"📊 Found {len(results)} matching posts (out of {len(posts)} total):")
            print("-" * 60)

            for i, post in enumerate(results[:10], 1):  # Show first 10
                username = post.get('author_username', 'unknown')
                platform = post.get('platform', 'unknown')
                date = post.get('posted_at_formatted', 'unknown')
                preview = post.get('text_preview', '')[:60]
                print(f"{i:2}. [@{username:15}] [{platform:8}] {date[:10]} | {preview}...")

            if len(results) > 10:
                print(f"\n... and {len(results) - 10} more results")
                print(f"Use 'show <number>' to see full details (1-10)")
            elif len(results) > 0:
                print(f"\nUse 'show <number>' to see full details (1-{min(len(results), 10)})")

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
