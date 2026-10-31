-- Retain every demographic record, including children and absent urine rows.
-- {weight} and {lab_columns} are validated identifiers supplied by the loader.
CREATE VIEW joined AS
SELECT d.*, {lab_columns},
       CASE WHEN l.SEQN IS NULL THEN 'left_only' ELSE 'both' END AS _merge
FROM demographics AS d
LEFT JOIN urine AS l ON d.SEQN = l.SEQN;

CREATE VIEW eligibility AS
SELECT *,
       COALESCE(RIDAGEYR >= 20, 0) AS is_adult,
       (is_finite({weight}) AND {weight} > 0) AS positive_mec,
       (is_finite(URXUMA) AND URXUMA >= 0 AND
        is_finite(URXUCR) AND URXUCR > 0) AS valid_urine,
       CASE WHEN RIDAGEYR >= 60 THEN '60+'
            WHEN RIDAGEYR >= 40 THEN '40-59'
            WHEN RIDAGEYR >= 20 THEN '20-39' END AS age_group
FROM joined;

CREATE VIEW concentrations AS
SELECT *, (is_adult AND positive_mec AND valid_urine) AS complete_adult,
       CASE WHEN valid_urine THEN URXUMA / URXUCR * 100.0 END AS raw_acr,
       CASE WHEN '{cycle}' = '2021-2023' AND valid_urine
            THEN -1.643 + 1.189 * URXUMA END AS bridge_unclipped
FROM eligibility;

CREATE VIEW ratios AS
SELECT *, CASE WHEN bridge_unclipped < 0 THEN 0.0
               ELSE bridge_unclipped END AS adjusted_albumin,
       CASE WHEN bridge_unclipped < 0 THEN 0.0
            ELSE bridge_unclipped / NULLIF(URXUCR, 0) * 100.0 END AS adjusted_acr
FROM concentrations;

CREATE VIEW participants AS
SELECT *, raw_acr >= 30.0 AS raw_positive,
       adjusted_acr >= 30.0 AS adjusted_positive,
       bridge_unclipped < 0 AS negative_adjusted_albumin
FROM ratios;
