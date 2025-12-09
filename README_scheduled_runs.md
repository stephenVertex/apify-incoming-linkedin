# Scheduled Data Downloads

This document describes the automated data collection jobs that run on a regular schedule to keep the social media database up to date.

## Overview

Two macOS LaunchAgents are configured to run every 6 hours:

1. **LinkedIn Data Updates** - Fetches posts from monitored LinkedIn profiles
2. **YouTube Data Updates** - Fetches new videos and updates statistics for monitored YouTube channels

## LaunchAgents Configuration

### 1. LinkedIn Data Updates

- **LaunchAgent**: `com.socialtui.updatedata`
- **Plist Location**: `~/Library/LaunchAgents/com.socialtui.updatedata.plist`
- **Script**: `update_data.py`
- **Schedule**: Every 6 hours (21,600 seconds)
- **Logs**:
  - Output: `logs/update_data.log`
  - Errors: `logs/update_data.error.log`

**What it does:**
- Runs the Apify LinkedIn scraper for monitored profiles
- Downloads new posts and media attachments
- Stores posts in the `posts` table
- Tracks engagement metrics in `data_downloads` table
- Records run history in `download_runs` table with `platform='linkedin'`

### 2. YouTube Data Updates

- **LaunchAgent**: `com.socialtui.updateyoutube`
- **Plist Location**: `~/Library/LaunchAgents/com.socialtui.updateyoutube.plist`
- **Script**: `run_youtube.sh` (wrapper)
- **Schedule**: Every 6 hours (21,600 seconds)
- **Logs**:
  - Output: `logs/update_youtube.log`
  - Errors: `logs/update_youtube.error.log`

**What it does:**
The wrapper script runs two Python scripts in sequence:

1. **`youtube_fetcher.py`** - Fetches new videos
   - Queries active YouTube channels from `profiles` table
   - Uses YouTube Data API to fetch videos from the last 5 days
   - Downloads video thumbnails to local cache
   - Inserts new videos into `posts` table
   - Creates initial stats snapshot in `data_downloads` table

2. **`update_youtube_stats.py`** - Updates existing video statistics
   - Queries existing YouTube videos from the last 30 days
   - Fetches current view counts, likes, and comments from YouTube API
   - Creates new time-series snapshots in `data_downloads` table
   - Records run history in `download_runs` table with `platform='youtube'`

## Managing LaunchAgents

### Check Status

View loaded LaunchAgents:
```bash
launchctl list | grep socialtui
```

Expected output:
```
-	0	com.socialtui.updateyoutube
-	0	com.socialtui.updatedata
```

### Unload (Stop) an Agent

```bash
launchctl unload ~/Library/LaunchAgents/com.socialtui.updatedata.plist
launchctl unload ~/Library/LaunchAgents/com.socialtui.updateyoutube.plist
```

### Load (Start) an Agent

```bash
launchctl load ~/Library/LaunchAgents/com.socialtui.updatedata.plist
launchctl load ~/Library/LaunchAgents/com.socialtui.updateyoutube.plist
```

### View Logs

```bash
# LinkedIn updates
tail -f logs/update_data.log
tail -f logs/update_data.error.log

# YouTube updates
tail -f logs/update_youtube.log
tail -f logs/update_youtube.error.log
```

### Check Recent Runs in Database

```sql
-- View recent runs for all platforms
SELECT run_id, started_at, completed_at, status, platform, script_name,
       posts_fetched, posts_new
FROM download_runs
ORDER BY started_at DESC
LIMIT 10;

-- View LinkedIn runs only
SELECT run_id, started_at, status, posts_fetched, posts_new
FROM download_runs
WHERE platform = 'linkedin'
ORDER BY started_at DESC
LIMIT 5;

-- View YouTube runs only
SELECT run_id, started_at, status, posts_fetched, posts_new
FROM download_runs
WHERE platform = 'youtube'
ORDER BY started_at DESC
LIMIT 5;
```

## Manual Execution

You can run any of the scripts manually for testing or immediate updates:

### LinkedIn Updates
```bash
uv run python3 update_data.py
```

### YouTube Updates
```bash
# Run the full wrapper script
./run_youtube.sh

# Or run individual scripts
uv run python3 youtube_fetcher.py
uv run python3 update_youtube_stats.py
```

### YouTube Script Options

**youtube_fetcher.py** supports custom date ranges:
```bash
# Fetch videos from the last 7 days instead of default 5
uv run python3 youtube_fetcher.py --days-back 7
```

**update_youtube_stats.py** has several options:
```bash
# Update only videos from the last 7 days
uv run python3 update_youtube_stats.py --days-back 7

# Update all videos regardless of age
uv run python3 update_youtube_stats.py --all

# Update only 100 most recent videos
uv run python3 update_youtube_stats.py --limit 100

# Update only a specific channel
uv run python3 update_youtube_stats.py --channel @amazonwebservices
```

## Environment Variables

Both systems require environment variables in `.env`:

```bash
# Supabase connection
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# LinkedIn scraper (Apify)
APIFY_API_TOKEN=your_apify_token

# YouTube Data API
YOUTUBE_API_KEY=your_youtube_api_key
```

## Database Tables

### posts
Primary table for all social media content (LinkedIn and YouTube).

Key fields:
- `post_id` - Unique identifier
- `urn` - Platform-specific identifier (LinkedIn URN or YouTube video ID)
- `platform` - 'linkedin' or 'youtube'
- `author_username` - Channel/profile username
- `posted_at_timestamp` - Unix timestamp (milliseconds)
- `text_content` - Post text or video title/description
- `url` - Link to original content

### download_runs
Audit trail of all scheduled and manual data collection runs.

Key fields:
- `run_id` - Unique run identifier
- `started_at`, `completed_at` - Timestamps
- `status` - 'running', 'completed', or 'failed'
- `platform` - 'linkedin' or 'youtube'
- `script_name` - Which script performed the run
- `posts_fetched`, `posts_new`, `posts_updated` - Statistics

### data_downloads
Time-series snapshots of engagement metrics.

Key fields:
- `download_id` - Unique snapshot identifier
- `post_id` - References `posts.post_id`
- `run_id` - References `download_runs.run_id`
- `downloaded_at` - When this snapshot was taken
- `total_reactions` - Likes/reactions count
- `stats_json` - Detailed platform-specific stats (views, comments, etc.)

## Troubleshooting

### Agent Not Running

1. Check if loaded: `launchctl list | grep socialtui`
2. Check logs for errors in `logs/*.error.log`
3. Verify plist file exists in `~/Library/LaunchAgents/`
4. Try unloading and reloading the agent

### API Errors

**LinkedIn (Apify)**:
- Verify `APIFY_API_TOKEN` in `.env`
- Check Apify account quota/credits
- Review `logs/update_data.error.log`

**YouTube**:
- Verify `YOUTUBE_API_KEY` in `.env`
- Check YouTube API quota (10,000 units/day free tier)
- Review `logs/update_youtube.error.log`
- Each video fetch uses ~1 unit, stats update uses ~1 unit per 50 videos

### Database Connection Issues

- Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Check network connectivity
- Verify project is not paused in Supabase dashboard

## Schedule Timeline

With both agents running every 6 hours, typical execution times (assuming first run at midnight):

```
00:00 - LinkedIn Update
00:00 - YouTube Update
06:00 - LinkedIn Update
06:00 - YouTube Update
12:00 - LinkedIn Update
12:00 - YouTube Update
18:00 - LinkedIn Update
18:00 - YouTube Update
```

Note: Exact times may vary slightly based on when the agents were initially loaded.

## TODO / Future Improvements

### Move to Supabase Edge Functions (Low Priority)

Currently, data collection runs on a local machine using macOS LaunchAgents. A potential improvement would be to migrate this to Supabase Edge Functions with scheduled execution.

**Benefits:**
- No dependency on local machine being online
- Centralized execution in the cloud
- Better monitoring and logging through Supabase dashboard
- No need to manage LaunchAgents locally
- Easier to scale and modify schedules

**Considerations:**
- Edge Functions would need access to:
  - Apify API for LinkedIn scraping
  - YouTube Data API for video fetching
  - Local media cache would need to move to Supabase Storage
- Supabase Edge Functions support cron schedules via `supabase functions deploy --schedule`
- API keys would be stored as Edge Function secrets
- Cost: Edge Function invocations and execution time (current local execution is free)

**Implementation approach:**
1. Create two Edge Functions:
   - `linkedin-updater` - Runs `update_data.py` logic
   - `youtube-updater` - Runs `youtube_fetcher.py` and `update_youtube_stats.py` logic
2. Convert Python scripts to TypeScript/Deno for Edge Functions
3. Set up cron schedules: `0 */6 * * *` (every 6 hours)
4. Migrate media caching to Supabase Storage
5. Test thoroughly before deprecating LaunchAgents

**Priority:** Low - Current LaunchAgent implementation is working well and reliable.
