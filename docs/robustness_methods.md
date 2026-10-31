# Robustness and reliability methods

From the project folder, run:

```powershell
.\scripts\validation\run_validation.ps1 -ReviewRobustness
```

**Output behaviour:** this command replaces the named robustness outputs and
reports, including the validation evidence that it reruns. Preserve an existing
run before using it.

This runs the R helper tests, rechecks the independent Python/R agreement,
then regenerates the robustness report and aggregate CSV tables. The launcher
finds R without fixed drive paths; its optional overrides are repository-relative.
See [the reproduction guide](reproduction.md) for exact runtime/package versions
and fresh-computer setup.

`scripts/validation/review_robustness.R` implements the robustness checks.
Interval and boundary calculations are defined in `reliability_helpers.R`.
Their tests are in `tests/test_reliability_helpers.R`.

## Statistical scope

**Reporting reliability** concerns how precisely a proportion is estimated.
The NCHS-style screen looks at actual and effective denominator size, absolute
and relative interval widths, events at a boundary and design degrees of freedom.
It also checks complementary proportions. It does not automatically suppress
an estimate merely because its numerator is below 30. Sparse event counts are reported alongside their intervals.

For binary outcomes we calculate Korn-Graubard beta intervals using effective
sample size and the finite-design-df correction used by survey 4.5. The effective
interval denominator is capped at the actual sample size. We cross-check against
`svyciprop(method="beta")` when its uncapped denominator does not exceed that
cap. Finite-df logit intervals are saved too. Our original primary t Wald intervals
remain clearly labelled rather than silently being replaced. Passing this screen
is a research reporting assessment, not official NCHS clearance.

The **paired difference** averages a variable that can be -1, 0 or +1. It is not
binary, so the proportion-screen thresholds are not applied to it.

**Missing-data robustness** asks whether observed results depend on assumptions
about adults whose urine results are unavailable. Two different checks are saved:

1. Response-cell weighting uses age group x sex x race/ethnicity. Within each
   cell, respondents represent all examined adults in that cell. The adjustment
   assumes that respondents and nonrespondents have comparable outcomes within
   cells. It cannot correct unmeasured reasons for nonresponse. Its intervals
   treat the estimated target cell totals as fixed and are diagnostic sensitivities.
2. A stress test lets the unknown missing group's mean paired change range from
   -1 (everyone reclassifies downward) to +1 (everyone reclassifies upward).
   It combines that assumed mean with the observed mean using their adult MEC
   weight shares. These are worst-case identification bounds, not confidence
   limits. The tipping mean shows the missing-group change needed to erase the
   overall point increase; it does not estimate what actually happened.

The demographic missingness table is descriptive. Similar rates cannot prove
that missingness is ignorable, and different rates do not by themselves specify
the missing-data mechanism.

## Saved results

- `report/robustness_reliability_review.md`: primary table, reporting screen,
  missingness findings, assay sensitivities and interpretation.
- `outputs/tables/reporting_reliability.csv`: numerator, denominator, event PSUs,
  effective size, relative standard error, intervals and screen decisions.
- `outputs/tables/missingness_demographic_review.csv`: group rates and intervals.
- `outputs/tables/response_cell_weighting_diagnostics.csv`: aggregate cell totals
  and response-weight multipliers used to assess cell coverage and adjustment size.
- `outputs/tables/response_weighting_sensitivity.csv`: adjusted outcome estimates.
- `outputs/tables/paired_missingness_stress_test.csv`: assumed missing-group changes
  and corresponding overall point differences.
- `outputs/tables/robustness_review_summary.json`: key summary values.
- `report/robustness_review_session.txt`: software versions.

All results are conditional on the chosen assay equation. None of these checks
propagates the bridging study's coefficient uncertainty or makes a clinical CKD
diagnosis from a single urine sample.

## References

- [NCHS proportion presentation standards](https://www.cdc.gov/nchs/data/series/sr_02/sr02_175.pdf).
- [NHANES reliability tutorial](https://wwwn.cdc.gov/nchs/nhanes/tutorials/reliabilityofestimates.aspx).
- [R survey package reference](https://cran.r-project.org/web/packages/survey/survey.pdf).
