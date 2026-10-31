SELECT COUNT(*) AS n_adults_with_valid_lab,
       COALESCE(SUM(raw_positive), 0) AS raw_above_30,
       COALESCE(SUM(adjusted_positive), 0) AS adjusted_above_30,
       COALESCE(SUM(NOT raw_positive AND adjusted_positive), 0) AS cross_below_to_above,
       COALESCE(SUM(raw_positive AND NOT adjusted_positive), 0) AS cross_above_to_below,
       COALESCE(SUM(raw_positive != adjusted_positive), 0) AS any_reclassification,
       COALESCE(SUM(negative_adjusted_albumin), 0) AS clipped_adjusted_albumin
FROM analysis_sample;
