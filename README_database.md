# Database Documentation & Troubleshooting

## Schema Overview

### Core Tables

#### `posts`
- **Purpose:** Core social media posts from monitored profiles.
- **Key Fields:**
  - `post_id` (PK), `urn` (Unique), `full_urn`
  - `posted_at_timestamp`: **Unix timestamp in milliseconds.**
  - `author_username`, `text_content`
  - `raw_json`: Complete post data as JSON.
  - `first_seen_at`: When this post was first imported.

#### `data_downloads`
- **Purpose:** Time-series snapshots of post engagement metrics.
- **Key Fields:**
  - `download_id` (PK), `post_id` (FK), `run_id` (FK)
  - `downloaded_at`: Timestamp of the snapshot.
  - `stats_json`: JSON string with detailed engagement metrics.

#### `download_runs`
- **Purpose:** Audit trail of data scraping/download sessions.

---

## Database Views

To improve performance and simplify application logic, the database uses views to pre-process data.

### `v_main_post_view`
- **Purpose:** Provides all data necessary for the main TUI post list.
- **Logic:**
  - Joins `posts` with `action_queue` (for marked status) and `post_media` (for media indicators).
  - **Corrects `posted_at_timestamp`** from milliseconds to a formatted string.
  - **Generates `media_indicator`** directly from `raw_json` in the `posts` table, bypassing the `post_media` table which may not be populated.
  - Consolidates marked actions into a single string.
  - Provides a 50-character `text_preview`.
- **Used by:** `interactive_posts.py` for the main `DataTable`.

### `post_engagement_history`
- **Purpose:** Provides a clean, time-series view of engagement for each post.
- **Logic:**
  - Joins `posts`, `data_downloads`, and `profiles`.
  - **Corrects `posted_at_timestamp`** from milliseconds to a valid timestamp.
  - **Parses `stats_json`** to extract key metrics (`total_reactions`, `comments`, `reposts`, `views`).
  - **Robustly calculates `total_reactions`** using `COALESCE` across multiple possible JSON keys.
  - Orders history chronologically (`ASC`) for timeline display.
- **Used by:** `interactive_posts.py` for the post detail screen.

---

## Data Flow

### Import Process
1.  **Scraper** → Generates JSON files.
2.  **Import Script** → Populates `posts`, `data_downloads`, etc.

### UI Loading (Optimized with Views)
1.  **Main List (`v_main_post_view`):**
    - The TUI runs a single query against the `v_main_post_view`.
    - This view provides pre-formatted and consolidated data, including `media_indicator` and `marked_indicator`, minimizing client-side processing.
    - The app separately fetches the `raw_json` for the selected posts to prepare for the detail view.
2.  **Engagement History (`post_engagement_history`):**
    - When a post is selected, the app queries the `post_engagement_history` view for that `post_id`.
    - The view returns clean, ordered, and parsed time-series data, which is immediately ready for display.

---

## Common Issues & Solutions

### Issue: Incorrect Dates in UI (e.g., Year 57886)

- **Symptom:** The UI displays dates far in the future.
- **Root Cause:** The `posts.posted_at_timestamp` column stores a Unix timestamp in **milliseconds**, but PostgreSQL's `to_timestamp()` function expects **seconds**.
- **Fix:** The database views (`v_main_post_view` and `post_engagement_history`) now correctly convert the timestamp by dividing by 1000.0 before formatting (`to_timestamp(posted_at_timestamp / 1000.0)`). This ensures the date is calculated correctly at the database level.

### Issue: Historical Tracking Data Not Displaying in UI

- **Symptom:** UI shows "(No historical tracking data available)".
- **Root Cause (Legacy):** Previously caused by incorrect multi-column ordering in the Supabase Python client.
- **Current Solution:** This is now handled by the `post_engagement_history` view, which correctly pre-sorts the data. The application code is much simpler and no longer relies on complex client-side sorting for this data.

---

## Supabase Python Client Gotchas

### Multi-Column Sorting
- **Wrong:** `.order('col1, col2')`
- **Right:** `.order('col1').order('col2')`

### JSON Column Handling
- **Storage:** JSON is stored as `TEXT`.
- **Parsing:** Application must use `json.loads()`.
- **PostgreSQL:** Use the `::jsonb` cast for querying JSON content, as done in the database views.

---
*Other sections like Deduplication Logic and Migration Notes remain unchanged.*
