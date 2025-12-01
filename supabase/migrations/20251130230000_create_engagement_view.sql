-- ============================================
-- View: v_post_engagement_history
-- ============================================
-- Purpose: Provides a clean, consolidated view of post engagement history,
-- extracting key metrics from the stats_json field for easier querying.
-- ============================================

CREATE OR REPLACE VIEW v_post_engagement_history AS
SELECT
    dd.post_id,
    p.urn AS post_urn,
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
    dd.stats_json,
    dd.download_id,
    dd.run_id
FROM
    data_downloads dd
JOIN
    posts p ON dd.post_id = p.post_id
ORDER BY
    dd.post_id,
    dd.downloaded_at;

COMMENT ON VIEW v_post_engagement_history IS 'Consolidated view of post engagement history with parsed metrics from JSON.';
