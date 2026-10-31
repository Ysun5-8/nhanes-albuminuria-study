-- Descriptive weighted percentages only; survey uncertainty is estimated in R/Python.
SELECT {group} AS group_label, COUNT(*) AS n_eligible,
       SUM(valid_urine) AS n_valid,
       100.0 * SUM(NOT valid_urine) / COUNT(*) AS missing_or_invalid_pct,
       100.0 * SUM(CASE WHEN NOT valid_urine THEN {weight} ELSE 0 END)
           / SUM({weight}) AS weighted_missing_or_invalid_pct
FROM participants
WHERE is_adult AND positive_mec
GROUP BY {group}
ORDER BY {group};
