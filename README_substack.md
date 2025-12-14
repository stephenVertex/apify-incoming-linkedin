# Substack Feed Reader

> **Status: Integrated**
> This functionality has been fully integrated into the main application. You can now add Substack profiles via the UI and fetch articles using `substack_fetcher.py`.

## Overview
This utility connects to Substack RSS feeds for configured profiles and retrieves the latest articles. It parses the feeds to extract article titles, links, and publication dates, storing them in the Supabase `posts` table.

## Files Involved
*   `substack_fetcher.py`: The main Python script that fetches and stores articles for all active Substack profiles.
*   `trilogy_substack_feed_reader.py`: (Deprecated) Original single-feed prototype.

## Dependencies
*   `feedparser`: Used for parsing the RSS feed data.

## Usage

### 1. Add Profiles
Use the main application UI (`main.py`) to add Substack profiles.
*   Go to Profile Management.
*   Press 'a' to add a profile.
*   Enter the Substack URL (e.g., `trilogyai.substack.com`). The system will automatically detect the platform.

### 2. Fetch Articles
To fetch articles for all active Substack profiles, run:

```bash
uv run python3 substack_fetcher.py
```

This will:
1.  Fetch all active profiles with `platform='substack'`.
2.  Parse their RSS feeds.
3.  Upsert articles into the `posts` table (avoiding duplicates).

## Data Structure
Articles are stored in the `posts` table with:
*   `platform`: 'substack'
*   `urn`: `substack:<username>:<article_slug>`
*   `text_content`: Article summary/description.
*   `url`: Link to the full article.

