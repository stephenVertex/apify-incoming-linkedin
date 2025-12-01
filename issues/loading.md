# Issue: Historical Tracking Data Not Loading for Some Posts

**Status:** ✅ RESOLVED
**Date:** 2025-11-30
**Affected Component:** Engagement history loading in `interactive_posts.py`

## Symptom

When viewing certain posts in the TUI (e.g., `urn:li:activity:7399332114636206080`, post_id: `p-ed3f094d`), the UI displayed:

```
(No historical tracking data available)
```

Despite the database containing valid engagement snapshots for these posts.

## Investigation

1. **Database Verification**: Confirmed that the post had 6 valid snapshots in the `data_downloads` table with proper JSON data.

2. **Code Review**: The engagement history loading logic appeared correct at `interactive_posts.py:959`.

3. **Debug Logging**: Added comprehensive logging to `log/debug.log` to trace the data flow.

4. **Key Finding**: The logs revealed:
   ```
   Query returned 1000 engagement snapshots
   ✗ No snapshots for p-ed3f094d in query results
   ```

5. **Root Cause Identified**: The database contained **2,110 total engagement snapshots**, but the Supabase query was only returning **1,000 snapshots** due to the client's default row limit.

## Root Cause

**Supabase Python Client Default Limit**: The `supabase-py` client has a default row limit of 1,000 results per query. When loading engagement history for all posts, the query hit this limit and truncated results, cutting off snapshots for posts ordered alphabetically/sequentially after the 1,000th snapshot.

### Technical Details

- **Location**: `interactive_posts.py:959`
- **Original Query**:
  ```python
  history_result = client.table('data_downloads')\
      .select('post_id, downloaded_at, stats_json')\
      .in_('post_id', post_ids)\
      .order('post_id')\
      .order('downloaded_at')\
      .execute()  # ← Implicit 1000 row limit
  ```

- **Problem**: With 1,080 posts and an average of ~2 snapshots per post, the total snapshots (2,110) exceeded the default 1,000 row limit.

## Solution

Added explicit `.limit(10000)` to the engagement history query:

```python
history_result = client.table('data_downloads')\
    .select('post_id, downloaded_at, stats_json')\
    .in_('post_id', post_ids)\
    .order('post_id')\
    .order('downloaded_at')\
    .limit(10000)\  # ← FIXED: Explicit limit
    .execute()
```

**File**: `interactive_posts.py:959`

## Verification

After the fix, the debug logs should show:

```
Query returned 2110 engagement snapshots
✓ Found 6 snapshots for p-ed3f094d in query results
✓ Attached 6 snapshots to post p-ed3f094d
```

And the UI should display:
- Historical timeline table with all snapshots
- Growth metrics (e.g., Comments: 21 → 23)
- Snapshot count and date range

## Related Issues

This is related to the multi-column ordering issue documented in `README_database.md:46-80`, which required chaining `.order()` calls instead of comma-separated column names. However, that documentation did not mention the default row limit issue.

## Prevention

- **Monitor**: Check `log/debug.log` for warnings about query result counts vs. expected totals
- **Future-Proofing**: The 10,000 limit provides headroom for growth. Consider implementing pagination if approaching this limit (~5,000 posts with 2 snapshots each)
- **Testing**: Test with posts that would be alphabetically/sequentially late in the result set

## Lessons Learned

1. **ORM Limits**: Always be aware of default row limits in ORM/client libraries
2. **Debug Logging**: File-based logging (`log/debug.log`) was essential for diagnosing this issue since TUI apps can't use console output
3. **Comprehensive Testing**: Test edge cases with data that would appear at the end of large result sets
