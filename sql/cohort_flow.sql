-- Counts describe the sample; they are not population prevalence estimates.
SELECT COUNT(*) AS n_demographics,
       COALESCE(SUM(is_adult), 0) AS n_adults_demographics,
       COALESCE(SUM(positive_mec), 0) AS n_full_mec_design,
       COALESCE(SUM(is_adult AND positive_mec), 0) AS n_adults_positive_mec_weight,
       COALESCE(SUM(complete_adult), 0) AS n_eligible_valid_lab,
       COALESCE(SUM(is_adult AND positive_mec AND NOT valid_urine), 0)
           AS n_eligible_missing_or_invalid_lab,
       COALESCE(SUM(is_adult AND positive_mec AND _merge = 'left_only'), 0)
           AS n_eligible_no_lab_row
FROM participants;
