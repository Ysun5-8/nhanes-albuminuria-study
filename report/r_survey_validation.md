# Independent R survey validation

Result: PASS

Compared 36 outcomes across six scenarios, with 216 numeric checks.
Failed numeric checks: 0. All design-count checks pass: TRUE.
Unweighted QC count comparisons: 7; failures: 0. Counts are calculated from data, not hard-coded.
Maximum absolute numeric difference: 2.776e-17 (proportion units for estimates and intervals).
Tolerance: 1.0e-10 + 1.0e-08 * abs(Python value); counts and degrees of freedom require exact agreement.

R independently read the original XPT files with foreign::read.xport, rebuilt the cohort and outcomes,
and estimated variances with survey::svymean. This checks data preparation and the custom Python variance calculation against a separate implementation under the shared protocol.

## Primary results

| Outcome | Estimate (%) or difference (percentage points) | 95% CI |
|---|---:|---:|
| raw_at_or_above_30 | 10.35393 | 9.35898 to 11.34889 |
| harmonised_at_or_above_30 | 11.41723 | 10.24797 to 12.58650 |
| paired_difference_harmonised_minus_raw | 1.06330 | 0.67701 to 1.44959 |
| any_reclassification | 1.23138 | 0.85254 to 1.61022 |
| below_to_above | 1.14734 | 0.77058 to 1.52410 |
| above_to_below | 0.08404 | 0.01757 to 0.15051 |

## Scope and limits

Both implementations were developed within this project. Their agreement checks implementation under the shared protocol; it is not an external scientific audit, does not establish that missingness is ignorable and does not validate the assay bridge.
The intervals are t Wald intervals with 15 design degrees of freedom. They condition on fixed bridge coefficients.
Reporting reliability is assessed separately in report/robustness_reliability_review.md; passing that research screen is not official publication clearance.

See r_validation_session.txt for package versions, outputs/tables/r_python_comparison.csv for every comparison,
and docs/r_validation_methods.md for an explanation and rerun instructions.

Official package reference: https://cran.r-project.org/web/packages/survey/survey.pdf
