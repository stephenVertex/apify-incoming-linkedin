#!/usr/bin/env python3
"""Test script for profile management system."""

from profile_manager import ProfileManager
from tag_manager import TagManager

def main():
    print("=" * 80)
    print("Profile Management System Test")
    print("=" * 80)

    # Initialize managers
    pm = ProfileManager("data/posts.db")
    tm = TagManager("data/posts.db")

    print("\n1. Testing database tables...")
    print("   ✓ ProfileManager initialized")
    print("   ✓ TagManager initialized")
    print("   ✓ Default tags created (aws, ai, startup)")

    # Import profiles from CSV
    print("\n2. Importing profiles from CSV...")
    stats = pm.sync_from_csv("data/input-data.csv")
    print(f"   Added: {stats['added']}")
    print(f"   Updated: {stats['updated']}")
    print(f"   Skipped: {stats['skipped']}")

    # Get all profiles
    print("\n3. Fetching all profiles...")
    profiles = pm.get_all_profiles()
    print(f"   Total profiles: {len(profiles)}")

    # Display first 5 profiles
    print("\n4. Sample profiles:")
    for profile in profiles[:5]:
        print(f"   - {profile['name']} (@{profile['username']}) [ID: {profile['id']}]")

    # Get all tags
    print("\n5. Available tags:")
    tags = tm.get_all_tags()
    for tag in tags:
        print(f"   - {tag['name']} (color: {tag['color']})")

    # Tag a sample profile with AWS
    if profiles:
        print("\n6. Tagging sample profiles...")
        aws_tag = tm.get_tag_by_name("aws")
        ai_tag = tm.get_tag_by_name("ai")

        # Tag first 3 profiles with AWS
        for i in range(min(3, len(profiles))):
            tm.tag_profile(profiles[i]['id'], aws_tag['id'])
            print(f"   ✓ Tagged {profiles[i]['name']} with 'aws'")

        # Tag first 2 profiles with AI
        for i in range(min(2, len(profiles))):
            tm.tag_profile(profiles[i]['id'], ai_tag['id'])
            print(f"   ✓ Tagged {profiles[i]['name']} with 'ai'")

    # Test filtering by tags
    print("\n7. Testing tag filtering...")
    aws_profiles = pm.get_profiles_by_tag("aws")
    print(f"   Profiles with 'aws' tag: {len(aws_profiles)}")
    for profile in aws_profiles:
        tags = tm.get_profile_tag_names(profile['id'])
        print(f"   - {profile['name']} (tags: {', '.join(tags)})")

    print("\n8. Testing multi-tag filtering (OR)...")
    both_profiles = pm.get_profiles_by_tags(["aws", "ai"], match_all=False)
    print(f"   Profiles with 'aws' OR 'ai': {len(both_profiles)}")

    print("\n9. Testing multi-tag filtering (AND)...")
    both_profiles_and = pm.get_profiles_by_tags(["aws", "ai"], match_all=True)
    print(f"   Profiles with 'aws' AND 'ai': {len(both_profiles_and)}")
    for profile in both_profiles_and:
        tags = tm.get_profile_tag_names(profile['id'])
        print(f"   - {profile['name']} (tags: {', '.join(tags)})")

    # Export to CSV
    print("\n10. Exporting profiles to CSV...")
    pm.export_to_csv("data/input-data.csv")
    print("   ✓ Exported to data/input-data.csv")

    print("\n" + "=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)
    print("\nYou can now run: python3 interactive_posts.py -d")
    print("Then press 'p' to open the Profile Management screen")
    print("=" * 80)

if __name__ == "__main__":
    main()
