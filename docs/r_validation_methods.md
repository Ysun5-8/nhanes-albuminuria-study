# R validation methods

## Scope

`scripts/validation/validate_with_r.R` independently rebuilds the analysis from
the original NHANES XPT files. It compares R's established `survey` package with
the Python implementation, including the primary analysis and five sensitivities.
The script covers import, cohort construction, survey design, estimation,
comparison and saved evidence.

## Statistical specification

WTMEC2YR supplies examination weights; interview-only participants have zero
weight. SDMVSTRA and nested SDMVPSU define stratification and clustering.
The design includes all positive-weight examination records before `subset()`
selects complete-data adults. This preserves PSUs with no domain participants
for variance estimation.

The paired outcome is each participant's `adjusted - raw` classification.
Its survey-weighted mean and variance retain the covariance between the two
classifications. Both implementations use t Wald intervals with explicitly
specified design degrees of freedom. A difference of 0.01063 in proportion
units is 1.063 percentage points, rather than a 1.063% relative increase.

R imports XPT files with `foreign::read.xport`; Python uses pandas. Separate
imports also check the handling of XPORT zero values, which the earlier pandas
run decoded as a small positive number. R does not reuse Python's cleaned data.

## How to rerun

**Before running:** this script replaces its CSV summaries, status JSON and
generated validation report/session record. The robustness launcher replaces
these too. Preserve an existing run before rerunning the analysis.

The simplest rerun is from a PowerShell terminal in the project folder:

```powershell
.\scripts\validation\run_validation.ps1
```

The launcher locates R without fixed drive paths and uses a repository-local
`.r-library` when present. Relative overrides are resolved from the repository,
even when you start it elsewhere. It restores your `R_LIBS_USER` setting on
success or failure and stops if an R command fails.

See [the reproduction guide](reproduction.md) for the observed Python and R
versions, exact required packages, setup instructions, all four raw downloads,
direct R commands and an explicit list of overwritten outputs. The launcher
does not install or update packages.

The Python reference file is `outputs/tables/paired_survey_analysis.json`. If you
change the Python analysis, review the proposed output changes and regenerate
that reference with the project's Python environment before rerunning validation. Do not edit reference numbers manually.
R does not download or modify raw NHANES data. Only aggregate results are saved.

## Validation records

- `report/r_survey_validation.md`: readable outcome and primary results.
- `outputs/tables/r_validation_status.json`: overall pass/fail, versions, source
  hashes and tolerances. The script exits with an error if a comparison fails.
- `outputs/tables/r_survey_results.csv`: 36 rows (six outcomes in six scenarios).
- `outputs/tables/r_python_comparison.csv`: 216 checks, including estimates,
  standard errors, confidence limits, domain counts and degrees of freedom.
- `outputs/tables/r_unweighted_qc_comparison.csv`: seven sample-count checks
  calculated independently in R and compared with the feasibility baseline.
- `report/r_validation_session.txt`: R and package versions used for this run.

For floating-point results, agreement means an absolute difference no larger than
`1e-10 + 1e-8 * abs(Python value)`. Counts and degrees of freedom must match
exactly. Tiny numerical differences arise from arithmetic order and are expected.

## Discrepancy assessment

Rows with `pass` equal to FALSE identify discrepancies. Differences in estimates
may arise from cohort counts, units, missingness or threshold conventions;
differences confined to standard errors may arise from weights, strata, PSU
nesting or domain construction. Interval-only differences may reflect the
critical value or degrees of freedom. Unexplained discrepancies remain failures
under the stated tolerances.

Agreement confirms the two implementations follow the same analysis choices.
It does not prove those choices eliminate selection bias, establish clinical
diagnoses, or include uncertainty in the bridge coefficients. Those are separate
scientific questions.

Official reference: https://cran.r-project.org/web/packages/survey/survey.pdf

## Cohort audit versus validation

`audit_cohort.py` records `demographics_before_lab_join` and mutually exclusive
`lab_record_categories` for both cycles. The feasibility pilot counts complete
laboratory participants and cannot supply an examination-response denominator.
Use the cohort audit when explaining missing urine results.

R and Python use separate data importers and variance implementations, but
they share this project's analysis plan. Agreement is an implementation check,
not an independent assessment of the plan's scientific assumptions.
