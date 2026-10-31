# Robustness and reporting-reliability review

## Validated primary results

| Outcome | Estimate (% or percentage points) | Original t Wald 95% CI |
|---|---:|---:|
| raw_at_or_above_30 | 10.3539 | 9.3590 to 11.3489 |
| harmonised_at_or_above_30 | 11.4172 | 10.2480 to 12.5865 |
| paired_difference_harmonised_minus_raw | 1.0633 | 0.6770 to 1.4496 |
| any_reclassification | 1.2314 | 0.8525 to 1.6102 |
| below_to_above | 1.1473 | 0.7706 to 1.5241 |
| above_to_below | 0.0840 | 0.0176 to 0.1505 |

## Proportion reporting screen

| Outcome | Events | Effective n used | KG 95% CI (%) | Screen |
|---|---:|---:|---:|---|
| raw | 721 | 3603.3 | 9.3778 to 11.3949 | present_screen_pass |
| harmonised | 786 | 2842.9 | 10.2708 to 12.6438 | present_screen_pass |
| upward | 71 | 3070.6 | 0.8015 to 1.5904 | present_screen_pass |
| downward | 6 | 5910.0 | 0.0272 to 0.1965 | present_screen_pass |
| reclassified | 77 | 3256.7 | 0.8815 to 1.6724 | present_screen_pass |

Downward reclassification occurs in 6 participants across 6 PSUs. RSE is 37.1%; KG relative interval width is 201.5%, but absolute width is only 0.169 percentage points.
A small nonzero numerator does not itself trigger suppression. The downward estimate remains sparse despite passing the screen; the event count and interval are reported without further subgroup analysis.
This is a transparent research reporting screen, not NCHS publication clearance. It uses effective-n beta intervals with the survey 4.5 finite-design-df adjustment and caps the interval denominator at actual n; complements are also checked. Finite-df logit intervals are saved as an additional sensitivity. The paired difference is not a binomial proportion, so these size/width rules are not applied to it.

## Missing-outcome robustness

Missing urine results account for 2.603% of adult MEC weight. Their unknown mean paired change would need to be -0.398 (-39.8 percentage points) to bring the overall point difference to zero.
Allowing that missing-group mean to range over [-1,1] gives all-examined-adult paired-change bounds of -1.567 to 3.638 percentage points. These are worst-case identification bounds, not confidence limits.
The observed positive change is not guaranteed under unrestricted missingness. These bounds do not assert that the most extreme assignments are plausible.
Age/sex/race response-cell weighting gives a paired difference of 1.066 percentage points, versus 1.063 before response adjustment. Largest cell weight multiplier: 1.083.
The response-cell analysis assumes exchangeability within cells. Its confidence intervals condition on estimated target totals; it cannot resolve nonignorable missingness.

## Assay and threshold sensitivities

| Sensitivity | Complete-data n | Paired change (percentage points) | t Wald 95% CI |
|---|---:|---:|---:|
| exclude_below_detection_either_analyte | 5484 | 1.153 | 0.737 to 1.570 |
| exclude_negative_bridge_values | 5484 | 1.153 | 0.737 to 1.570 |
| strictly_greater_than_30 | 5910 | 1.072 | 0.683 to 1.461 |
| published_rounded_raw_URDACT | 5910 | 1.063 | 0.677 to 1.450 |
| unclipped_bridge | 5910 | 1.063 | 0.677 to 1.450 |

## Descriptive missingness by demographics

| Demographic | Group | Missing / examined | Weighted missing (%) |
|---|---|---:|---:|
| age_group | 20-39 | 35 / 1559 | 2.650 |
| age_group | 40-59 | 33 / 1733 | 1.762 |
| age_group | 60+ | 86 / 2772 | 3.454 |
| sex | Male | 70 / 2720 | 2.702 |
| sex | Female | 84 / 3344 | 2.509 |
| race_ethnicity | Mexican American | 12 / 405 | 3.205 |
| race_ethnicity | Other Hispanic | 15 / 614 | 3.268 |
| race_ethnicity | Non-Hispanic White | 85 / 3569 | 2.312 |
| race_ethnicity | Non-Hispanic Black | 19 / 753 | 2.712 |
| race_ethnicity | Non-Hispanic Asian | 8 / 335 | 1.703 |
| race_ethnicity | Other/multiracial | 15 / 388 | 4.415 |

These descriptive differences do not establish that missingness is ignorable. See the saved CSV for design-based intervals; subgroup intervals are not used as a missing-data mechanism test.

## Interpretation

The primary finding is the paired increase among adults with complete urine data. Response weighting, worst-case missing-outcome bounds and assay/threshold sensitivities describe its dependence on the analysis assumptions. Sampling confidence intervals exclude bridge uncertainty and missing-data bias. Single urine measurements do not diagnose CKD.

## Reproduction and references

Run Rscript scripts/validation/review_robustness.R <project-root>. Run Rscript tests/test_reliability_helpers.R <project-root> for helper checks. All CSV outputs are aggregates in outputs/tables/; no raw data are modified.
NCHS proportion standards: https://www.cdc.gov/nchs/data/series/sr_02/sr02_175.pdf
NHANES reliability tutorial: https://wwwn.cdc.gov/nchs/nhanes/tutorials/reliabilityofestimates.aspx
R survey methods: https://cran.r-project.org/web/packages/survey/survey.pdf
