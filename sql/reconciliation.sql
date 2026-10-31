-- Usage vs. billed reconciliation for Andina Telecom (synthetic data).
-- One row per active subscriber and month, with expected vs. billed amount and a leak class.
-- Tables: subscribers, usage, bills, rates (plan_id, month, monthly_fee, data_rate, voice_rate, sms_rate)

WITH expected AS (
    SELECT
        u.subscriber_id,
        u.month,
        s.plan_id,
        s.segment,
        r.monthly_fee
          + u.data_gb   * r.data_rate
          + u.voice_min * r.voice_rate
          + u.sms       * r.sms_rate                         AS gross_expected,
        s.discount_pct,
        u.data_gb, u.voice_min, u.sms,
        r.data_rate, r.voice_rate
    FROM usage u
    JOIN subscribers s ON s.subscriber_id = u.subscriber_id AND s.status = 'active'
    JOIN rates r       ON r.plan_id = s.plan_id AND r.month = u.month
),
billed AS (
    SELECT
        b.*,
        b.fee_billed
          + b.data_gb_billed   * b.data_rate_applied
          + b.voice_min_billed * b.voice_rate_applied
          + b.sms_billed       * b.sms_rate_applied
          - b.discount_applied                               AS net_billed
    FROM bills b
)
SELECT
    e.subscriber_id,
    e.month,
    e.plan_id,
    e.segment,
    ROUND(e.gross_expected * (1 - e.discount_pct), 2)        AS net_expected,
    ROUND(COALESCE(b.net_billed, 0), 2)                      AS net_billed,
    ROUND(e.gross_expected * (1 - e.discount_pct) - COALESCE(b.net_billed, 0), 2) AS leakage,
    CASE
        WHEN b.subscriber_id IS NULL                                   THEN 'active_not_billed'
        WHEN ABS(b.data_rate_applied - e.data_rate) > 1e-9
          OR ABS(b.voice_rate_applied - e.voice_rate) > 1e-9           THEN 'stale_tariff'
        WHEN b.data_gb_billed < e.data_gb - 0.001
          OR b.voice_min_billed < e.voice_min - 0.05
          OR b.sms_billed < e.sms                                      THEN 'unbilled_usage'
        WHEN b.discount_applied > ROUND(e.gross_expected * e.discount_pct, 2) + 0.01
                                                                       THEN 'duplicate_discount'
        ELSE 'ok'
    END                                                      AS leak_class
FROM expected e
LEFT JOIN billed b ON b.subscriber_id = e.subscriber_id AND b.month = e.month;
