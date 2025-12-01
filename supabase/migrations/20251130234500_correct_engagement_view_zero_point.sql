-- Description: Corrects the logic in v_post_engagement_history to ensure the virtual 'zero point'
-- is always the first point in the timeline.

-- Drop the existing view
DROP VIEW IF EXISTS v_post_engagement_history;

-- Create the new, corrected view
CREATE OR REPLACE VIEW v_post_engagement_history AS
WITH post_min_timestamp AS (
    -- First, find the earliest real download timestamp for each post
    SELECT
        p.post_id,
        MIN(dd.downloaded_at) as min_downloaded_at
    FROM posts p
    LEFT JOIN data_downloads dd ON p.post_id = dd.post_id
    GROUP BY p.post_id
)
-- This part of the UNION creates the virtual 'zero point' for each post
SELECT
    p.post_id,
    p.urn AS post_urn,
    p.author_username,
    -- Set the zero point's timestamp to be 1 second before the first real data point.
    -- If no real data exists, use the post's creation time.
    (COALESCE(pmt.min_downloaded_at, to_timestamp(p.posted_at_timestamp / 1000.0) AT TIME ZONE 'UTC') - INTERVAL '1 second') as downloaded_at,
    0 AS reactions,
    0 AS comments,
    0 AS reposts,
    0 AS views,
    '{}'::jsonb AS stats_json,
    'virtual_initial_point' AS download_id,
    NULL AS run_id
FROM
    posts p
JOIN
    post_min_timestamp pmt ON p.post_id = pmt.post_id

UNION ALL

-- This part includes the actual engagement data from data_downloads
SELECT
    dd.post_id,
    p.urn AS post_urn,
    p.author_username,
    dd.downloaded_at,
    CASE
        WHEN dd.total_reactions IS NOT NULL AND dd.total_reactions > 0 THEN dd.total_reactions
        ELSE COALESCE(
            (dd.stats_json::jsonb ->> 'total_reactions')::integer,
            (dd.stats_json::jsonb ->> 'reactions')::integer,
            0
        )
    END AS reactions,
    COALESCE((dd.stats_json::jsonb ->> 'comments')::integer, 0) AS comments,
    COALESCE((dd.stats_json::jsonb ->> 'reposts')::integer, (dd.stats_json::jsonb ->> 'shares')::integer, 0) AS reposts,
    COALESCE((dd.stats_json::jsonb ->> 'views')::integer, 0) AS views,
    dd.stats_json::jsonb,
    dd.download_id,
    dd.run_id
FROM
    data_downloads dd
JOIN
    posts p ON dd.post_id = p.post_id;

COMMENT ON VIEW v_post_engagement_history IS 'Consolidated view of post engagement history, including a corrected virtual zero point.';
