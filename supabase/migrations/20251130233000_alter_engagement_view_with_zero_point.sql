-- Description: Alters the v_post_engagement_history view to include a virtual 'zero point'
-- at the time of posting, ensuring every timeline starts with zero engagement metrics.

-- Drop the existing view
DROP VIEW IF EXISTS v_post_engagement_history;

-- Create the new view with the zero point logic
CREATE OR REPLACE VIEW v_post_engagement_history AS
-- This part of the UNION creates the virtual 'zero point' for each post
SELECT
    p.post_id,
    p.urn AS post_urn,
    p.author_username,
    -- Convert millisecond timestamp to a proper timestamp with timezone
    to_timestamp(p.posted_at_timestamp / 1000.0) AT TIME ZONE 'UTC' as downloaded_at,
    0 AS reactions,
    0 AS comments,
    0 AS reposts,
    0 AS views,
    '{}'::jsonb AS stats_json,
    'virtual_initial_point' AS download_id,
    NULL AS run_id
FROM
    posts p

UNION ALL

-- This part includes the actual engagement data from data_downloads
SELECT
    dd.post_id,
    p.urn AS post_urn,
    p.author_username,
    dd.downloaded_at,
    -- Use total_reactions column, but fall back to JSON if it's zero or null
    CASE
        WHEN dd.total_reactions IS NOT NULL AND dd.total_reactions > 0 THEN dd.total_reactions
        ELSE COALESCE(
            (dd.stats_json::jsonb ->> 'total_reactions')::integer,
            (dd.stats_json::jsonb ->> 'reactions')::integer,
            0
        )
    END AS reactions,
    -- Extract and cast values from stats_json, handling missing keys with COALESCE and defaulting to 0
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

COMMENT ON VIEW v_post_engagement_history IS 'Consolidated view of post engagement history, including a virtual zero point at creation time.';
