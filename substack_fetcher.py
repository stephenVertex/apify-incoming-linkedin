"""Substack data fetcher for social-tui."""

import feedparser
import json
import logging
from datetime import datetime, timezone
from time import mktime
from typing import List, Dict, Any, Optional

from supabase_client import get_supabase_client
from db_utils import generate_aws_id, PREFIX_POST

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SubstackFetcher:
    """Fetcher for Substack RSS feeds."""

    def __init__(self):
        """Initialize with Supabase client."""
        self.client = get_supabase_client()

    def get_active_substack_profiles(self) -> List[Dict[str, Any]]:
        """Fetch all active profiles with platform='substack'.

        Returns:
            List of profile dictionaries.
        """
        response = self.client.table('profiles') \
            .select('*') \
            .eq('platform', 'substack') \
            .eq('is_active', True) \
            .execute()
        return response.data

    def fetch_feed(self, username: str) -> Optional[feedparser.FeedParserDict]:
        """Fetch and parse RSS feed for a Substack username.

        Args:
            username: Substack subdomain (e.g. 'trilogyai')

        Returns:
            Parsed feed object or None if failed.
        """
        url = f"https://{username}.substack.com/feed"
        try:
            logger.info(f"Fetching feed for {username}: {url}")
            feed = feedparser.parse(url)
            if feed.bozo:
                logger.warning(f"Feed parsing error for {username}: {feed.bozo_exception}")
                # Continue anyway as feedparser often returns usable data even with errors
            return feed
        except Exception as e:
            logger.error(f"Error fetching feed for {username}: {e}")
            return None

    def process_entry(self, entry: Dict[str, Any], profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert RSS entry to Post dictionary.

        Args:
            entry: Single feed entry
            profile: Profile dictionary

        Returns:
            Dictionary ready for 'posts' table upsert, or None if invalid.
        """
        try:
            # Generate URN
            # entry.id is usually the URL, but let's use a safe fallback
            # Substack GUIDs are usually URLs like https://trilogyai.substack.com/p/article-slug
            article_id = entry.get('id', entry.get('link'))
            if not article_id:
                logger.warning(f"Skipping entry without ID or Link: {entry.get('title')}")
                return None
            
            # Create a deterministic URN: substack:<username>:<hash_of_id> 
            # OR simpler: use the link if it's stable. 
            # The spec said: substack:<username>:<article_slug_or_hash>
            # Let's try to extract slug from link if possible
            slug = article_id.split('/')[-1]
            urn = f"substack:{profile['username']}:{slug}"

            # Parse timestamp
            published_struct = entry.get('published_parsed')
            if published_struct:
                posted_at_timestamp = int(mktime(published_struct))
                # Create timezone-aware datetime object
                posted_at_dt = datetime.fromtimestamp(posted_at_timestamp, tz=timezone.utc)
            else:
                posted_at_timestamp = int(datetime.now(timezone.utc).timestamp())
                posted_at_dt = datetime.now(timezone.utc)

            # Prepare content
            text_content = entry.get('summary', '') or entry.get('description', '')
            
            return {
                'urn': urn,
                'platform': 'substack',
                'posted_at_timestamp': posted_at_timestamp,
                'author_username': profile['username'],
                'text_content': text_content,
                'post_type': 'article',
                'url': entry.get('link'),
                'raw_json': json.dumps(entry),
                # Note: We don't set created_at here, let DB handle defaults for new rows
                # For updates, we update updated_at
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error processing entry {entry.get('title', 'Unknown')}: {e}")
            return None

    def save_post(self, post_data: Dict[str, Any]) -> str:
        """Upsert post to Supabase.

        Args:
            post_data: Dictionary of post fields

        Returns:
            Status string: 'created', 'updated', or 'error'
        """
        try:
            # Check if post exists by URN
            existing = self.client.table('posts').select('post_id').eq('urn', post_data['urn']).execute()
            
            if existing.data:
                # Update
                post_id = existing.data[0]['post_id']
                self.client.table('posts').update(post_data).eq('post_id', post_id).execute()
                return 'updated'
            else:
                # Insert
                post_data['post_id'] = generate_aws_id(PREFIX_POST)
                post_data['created_at'] = datetime.now(timezone.utc).isoformat()
                # Default fields
                post_data['is_read'] = False
                post_data['is_marked'] = False
                
                self.client.table('posts').insert(post_data).execute()
                return 'created'
                
        except Exception as e:
            logger.error(f"Error saving post {post_data.get('urn')}: {e}")
            return 'error'

    def run(self):
        """Main execution method."""
        profiles = self.get_active_substack_profiles()
        logger.info(f"Found {len(profiles)} active Substack profiles.")

        stats = {'created': 0, 'updated': 0, 'error': 0, 'total': 0}

        for profile in profiles:
            logger.info(f"Processing profile: {profile['username']}")
            feed = self.fetch_feed(profile['username'])
            
            if not feed:
                continue

            for entry in feed.entries:
                post_data = self.process_entry(entry, profile)
                if post_data:
                    status = self.save_post(post_data)
                    stats[status] += 1
                    stats['total'] += 1
        
        logger.info(f"Run complete. Stats: {stats}")

if __name__ == "__main__":
    fetcher = SubstackFetcher()
    fetcher.run()
