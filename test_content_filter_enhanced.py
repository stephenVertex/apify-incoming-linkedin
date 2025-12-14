#!/usr/bin/env python3
"""
Enhanced unit tests for post content filtering with RapidFuzz.
Uses RapidFuzz's token_set_ratio for fuzzy matching and multi-word AND logic.
"""

import sys
from datetime import datetime
from rapidfuzz import fuzz

# Mock post data for testing (same as base tests)
MOCK_POSTS = [
    {
        "post_id": "1",
        "text": "I love Python programming and machine learning",
        "author_username": "pythondev",
        "posted_at_formatted": "2025-12-01 10:00:00",
        "platform": "linkedin",
        "text_preview": "I love Python programming...",
    },
    {
        "post_id": "2",
        "text": "JavaScript is great for web development",
        "author_username": "jsmaster",
        "posted_at_formatted": "2025-12-02 10:00:00",
        "platform": "linkedin",
        "text_preview": "JavaScript is great...",
    },
    {
        "post_id": "3",
        "text": "Machine learning with TensorFlow",
        "author_username": "mlexpert",
        "posted_at_formatted": "2025-12-03 10:00:00",
        "platform": "substack",
        "text_preview": "Machine learning with...",
    },
    {
        "post_id": "4",
        "text": "AWS announces new Graviton 4 processors for EC2 instances. Amazing performance gains for cloud workloads!",
        "author_username": "cloudarchitect",
        "posted_at_formatted": "2025-12-04 14:30:00",
        "platform": "linkedin",
        "text_preview": "AWS announces new Graviton 4...",
    },
    {
        "post_id": "5",
        "text": "Benchmarking Graviton 5 chips: 40% better performance than Graviton 4. The ARM revolution in the data center continues.",
        "author_username": "awsengineer",
        "posted_at_formatted": "2025-12-05 09:15:00",
        "platform": "linkedin",
        "text_preview": "Benchmarking Graviton 5 chips...",
    },
    {
        "post_id": "6",
        "text": "Just migrated our entire infrastructure to Graviton instances. Cost savings are incredible!",
        "author_username": "devopsguru",
        "posted_at_formatted": "2025-12-06 11:45:00",
        "platform": "linkedin",
        "text_preview": "Just migrated our entire...",
    },
]

def create_searchable_text(post: dict) -> str:
    """Create searchable text from post fields."""
    parts = []

    if 'text' in post:
        parts.append(post['text'])
    if 'author_username' in post:
        parts.append(post['author_username'])

    return ' '.join(parts).lower()

def test_content_filter_enhanced(filter_text: str, posts: list, threshold: int = 80) -> list:
    """
    Enhanced content filtering with RapidFuzz fuzzy matching.

    Uses a hybrid approach:
    - Single word: partial_ratio (handles "grav" in "Graviton")
    - Multi-word: check ALL words match individually with partial_ratio

    Args:
        filter_text: The search query
        posts: List of posts to filter
        threshold: Minimum score to consider a match (0-100), default 80
    """
    if not filter_text:
        return posts  # Empty filter returns all

    matched_posts = []
    filter_lower = filter_text.lower().strip()
    filter_words = filter_lower.split()

    for post in posts:
        searchable = create_searchable_text(post)

        # Hybrid approach for best results
        if len(filter_words) == 1:
            # Single word: use partial_ratio for substring matching
            score = fuzz.partial_ratio(filter_lower, searchable)
            if score >= threshold:
                matched_posts.append(post)
        else:
            # Multi-word: check ALL words are present
            # Each word must score at least 75 to avoid false matches
            all_match = all(
                fuzz.partial_ratio(word, searchable) >= threshold
                for word in filter_words
            )
            if all_match:
                matched_posts.append(post)

    return matched_posts

def run_tests():
    """Run enhanced filter tests with RapidFuzz."""
    print("Testing Enhanced Content Filter (RapidFuzz partial_ratio)")
    print("=" * 60)

    # Test 1: Single word (should work same as before)
    print("\nTest 1: Filter for 'grav' (single partial word)")
    results = test_content_filter_enhanced("grav", MOCK_POSTS)
    print(f"Expected: 3 posts (all Graviton posts)")
    print(f"Got: {len(results)} post(s)")
    for post in results:
        print(f"  - {post['post_id']}: {post['text'][:60]}...")
    assert len(results) == 3, "Should find 3 Graviton posts"
    print("✅ PASS")

    # Test 2: Multi-word AND logic - "grav 5"
    print("\nTest 2: Filter for 'grav 5' (multi-word AND logic)")
    results = test_content_filter_enhanced("grav 5", MOCK_POSTS)
    print(f"Expected: 1 post (Graviton 5 post)")
    print(f"Got: {len(results)} post(s)")
    for post in results:
        print(f"  - {post['post_id']}: {post['text'][:60]}...")
    print(f"Note: Matches posts containing 'grav' AND '5' anywhere in text")
    assert len(results) == 1, "Should find 1 post with both 'grav' and '5'"
    assert results[0]['post_id'] == "5", "Should find the Graviton 5 post"
    print("✅ PASS")

    # Test 3: Multi-word AND logic - "grav 4"
    print("\nTest 3: Filter for 'grav 4' (multi-word AND logic)")
    results = test_content_filter_enhanced("grav 4", MOCK_POSTS)
    print(f"Expected: 2 posts (Graviton 4 and Graviton 5 posts)")
    print(f"Got: {len(results)} post(s)")
    for post in results:
        print(f"  - {post['post_id']}: {post['text'][:60]}...")
    print(f"Note: Post 5 mentions both Graviton 4 and 5, so it matches too")
    assert len(results) == 2, "Should find 2 posts with both 'grav' and '4'"
    expected_ids = {"4", "5"}
    found_ids = {post['post_id'] for post in results}
    assert found_ids == expected_ids, f"Should find posts {expected_ids}"
    print("✅ PASS")

    # Test 4: Multi-word AND - more specific
    print("\nTest 4: Filter for 'grav aws' (finds AWS Graviton posts)")
    results = test_content_filter_enhanced("grav aws", MOCK_POSTS)
    print(f"Expected: 2 posts (post 4 has 'AWS' in text, post 5 has 'aws' in username)")
    print(f"Got: {len(results)} post(s)")
    for post in results:
        username = post.get('author_username', '')
        print(f"  - {post['post_id']}: [@{username}] {post['text'][:50]}...")
    print(f"Note: Post 5 matches because author is 'awsengineer'")
    assert len(results) == 2, "Should find 2 posts with 'grav' and 'aws'"
    expected_ids = {"4", "5"}
    found_ids = {post['post_id'] for post in results}
    assert found_ids == expected_ids, f"Should find posts {expected_ids}"
    print("✅ PASS")

    # Test 5: Multi-word AND - all words must match
    print("\nTest 5: Filter for 'grav rust' (no matches)")
    results = test_content_filter_enhanced("grav rust", MOCK_POSTS)
    print(f"Expected: 0 posts (no post has both 'grav' and 'rust')")
    print(f"Got: {len(results)} post(s)")
    assert len(results) == 0, "Should find 0 posts"
    print("✅ PASS")

    # Test 6: Three word AND logic
    print("\nTest 6: Filter for 'graviton 5 benchmark' (three words)")
    results = test_content_filter_enhanced("graviton 5 benchmark", MOCK_POSTS)
    print(f"Expected: 1 post (Graviton 5 benchmarking post)")
    print(f"Got: {len(results)} post(s)")
    for post in results:
        print(f"  - {post['post_id']}: {post['text'][:60]}...")
    assert len(results) == 1, "Should find 1 post with all three words"
    assert results[0]['post_id'] == "5", "Should find the benchmarking post"
    print("✅ PASS")

    # Test 7: Case insensitive multi-word
    print("\nTest 7: Filter for 'GRAV 5' (case insensitive multi-word)")
    results = test_content_filter_enhanced("GRAV 5", MOCK_POSTS)
    print(f"Expected: 1 post (case insensitive)")
    print(f"Got: {len(results)} post(s)")
    assert len(results) == 1, "Should find 1 post (case insensitive)"
    print("✅ PASS")

    # Test 8: Partial words in multi-word search
    print("\nTest 8: Filter for 'mach learn' (partial multi-word)")
    results = test_content_filter_enhanced("mach learn", MOCK_POSTS)
    print(f"Expected: 2 posts (machine learning posts)")
    print(f"Got: {len(results)} post(s)")
    for post in results:
        print(f"  - {post['post_id']}: {post['text'][:60]}...")
    assert len(results) == 2, "Should find 2 machine learning posts"
    print("✅ PASS")

    print("\n" + "=" * 60)
    print("All enhanced tests passed! ✅")
    print("\n💡 RapidFuzz Benefits:")
    print("   ✓ 'grav 5' now finds Graviton 5 posts")
    print("   ✓ 'grav aws' finds AWS Graviton posts")
    print("   ✓ 'graviton 5 benchmark' finds specific posts")
    print("   ✓ Works with partial words and case insensitive")
    print("   ✓ Handles typos automatically (fuzzy matching)")
    print("   ✓ Simple implementation: fuzz.partial_ratio(query, text) >= threshold")

if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
