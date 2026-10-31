# NHANES urine albumin assay harmonisation protocol

This analysis plan follows an exploratory pilot; it is
not a prospective preregistration. Pilot reclassification counts were already known.

## Question and estimands

The analysis estimates how mapping urine albumin onto the earlier assay scale
changes the proportion of adults aged >=20 with single-specimen UACR >=30 mg/g
in August 2021-August 2023. Estimands are the paired change (harmonised minus raw),
any classification change and each direction of change. These are assay-scale comparisons,
not diagnoses of persistent albuminuria or CKD. The 2017-March 2020 release is a
reference cycle for feasibility; no cross-cycle trend inference is included here.

## Cohort and missingness

Laboratory records are joined one-to-one onto demographics by SEQN; people
without laboratory records remain in the cohort audit. The exact XPORT zero
sentinel `16**-65` produced by this pandas reader is restored to zero before weight
eligibility or detection-flag checks. Other small concentrations are unchanged.
Positive finite MEC weights are checked against RIDSTATR=2. Valid urine data
require finite nonnegative albumin and finite strictly positive creatinine.

The cohort audit records flow, nonresponse patterns and missingness by age, sex
and race/ethnicity for both cycles, separating lack of examination from urine
item nonresponse.
Primary estimates use complete urine data and the released MEC weights without
additional item nonresponse adjustment. Population interpretation therefore relies
on residual urine nonresponse being ignorable. Extreme missing-outcome
prevalence bounds are reported as sensitivity bounds, not confidence intervals.

## Laboratory conventions

`URXUMA` is urine albumin in micrograms/mL, numerically equal to mg/L.
`URXUCR` is urine creatinine in mg/dL; the factor 100 converts their ratio
to UACR in mg/g. `URDUMALC` codes albumin detection status: 0 means at or
above the detection limit, 1 means below it, and missing means unavailable.
`URDUCRLC` provides the corresponding creatinine flag. Below-detection results
are retained at the released CDC LLOD/sqrt(2) fill values in primary analysis;
the exclusion sensitivity requires both flags to equal zero.

The backward weighted Deming equation below comes from the ALB_CR_L Analytic
Notes, based on a 195-specimen bridging study. It maps the 2021-2023 assay to
the earlier assay scale; the forward equation addresses the reverse mapping.

Released albumin values, including CDC's below-detection substitutions, are used
without further imputation. Both detection flags are retained. The 2021-2023
documentation gives albumin LLOD=0.02 mg/L and creatinine LLOD=1.1 mg/dL.
Missing results remain missing.

Raw UACR is `100 * URXUMA / URXUCR`. Albumin is mapped to the older assay scale
using `-1.643 + 1.189 * URXUMA`; creatinine is unchanged. In the primary analysis,
negative converted albumin is clipped to zero and affected observations are flagged.
Clipping is an analysis convention, not a CDC clinical rule. UACR is unrounded
when the inclusive threshold `>=30 mg/g` is applied; equality counts as positive.
Published rounded URDACT is used only for quality control and sensitivity analysis.

## Survey estimation

WTMEC2YR is used for 2021-2023 and WTMECPRP for the pre-pandemic reference cycle,
without pooling or rescaling weights across cycles. All positive finite
MEC-weight records, including children and adults with missing laboratory results,
remain in the design. Complete-data adults form an analysis domain. The design
uses SDMVSTRA and nested SDMVPSU; missing design fields or singleton strata stop
the analysis.

Each outcome is estimated as a domain weighted mean. The paired difference is
calculated from each person's harmonised indicator minus their raw indicator,
retaining covariance between classifications. Taylor linearisation sums
`w*domain*(y-mean)/sum(w*domain)` by PSU, then sums within-stratum PSU squared
deviations with multiplier `m/(m-1)`. Out-of-domain records have zero linearised
contribution, while their PSUs remain in the calculation.
Variance uses a with-replacement first-stage approximation without a finite
population correction. Two-sided t Wald 95% intervals use df=sum(PSUs minus one
per stratum). Proportions are expressed as percentages and differences as
percentage points. Wald intervals are not truncated to parameter bounds and are
approximate, particularly for rare directional changes. The subsequent reporting
review assesses those proportions against the NCHS framework.

## Sensitivities and limits

Sensitivities exclude below-detection observations for either analyte, exclude
negative bridge predictions, omit clipping, apply strict `>30`, or use published
rounded raw UACR. Exclusions change the analysis domain; each scenario reports its
sample size. Missing-outcome prevalence bounds cover all examined adults.
Bridge coefficients are treated as fixed, so reported CIs reflect sampling
uncertainty only. Bridge uncertainty is not propagated; the public marginal coefficient
intervals do not supply their joint covariance. A full bridge-uncertainty analysis
would require additional validation data. The analysis supports neither causal
inference nor clinical diagnosis.

## Reproduction

Use the project Python environment from the repository root. The
[reproduction guide](reproduction.md) records the actual Python 3.12.10 and
R 4.6.1 runtimes, package versions, official raw downloads and portable R
launcher behaviour. The commands below assume the Python environment is active;
the guide also gives explicit interpreter paths without activation:

**Output behaviour:** the commands below replace named aggregate results and
generated reports. The robustness script also reruns validation. Use a separate
review root when preserving an existing run.

```powershell
python -m scripts.pilot.audit_cohort
python -m scripts.pilot.check_feasibility
python -m scripts.paired_analysis
python -m unittest discover -s tests -v
.\scripts\validation\run_validation.ps1 -ReviewRobustness
```

Outputs contain aggregate results only in `outputs/tables/`.
The older `data_quality_summary.json` used all 7,809 demographic adults as its
missingness denominator; use `mec_missingness_audit.json` for eligibility flow.

## Sources checked

- [CDC ALB_CR_L documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/ALB_CR_L.htm): assay bridge, units, detection limits and laboratory conventions.
- [CDC pre-pandemic urine laboratory documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_ALB_CR.htm): reference-cycle laboratory eligibility.
- [CDC DEMO_L documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DEMO_L.htm): examination status and survey design fields.
- [CDC variance estimation tutorial](https://wwwn.cdc.gov/nchs/nhanes/tutorials/varianceestimation.aspx): domain estimation and Taylor variance.

## Independent validation

R 4.6.1 with survey 4.5 independently reproduced the primary analysis and all five
sensitivities from the original XPT files. All 216 comparisons passed; see
report/r_survey_validation.md. Run scripts/validation/run_validation.ps1 to repeat the
check; docs/r_validation_methods.md explains the steps.

## Post-pilot robustness and reporting review

The follow-up review uses Korn-Graubard beta proportion intervals with the
finite-design-df adjustment implemented in survey 4.5, an interval-denominator cap at
actual n, complementary-proportion checks, and finite-df logit intervals as a
sensitivity. The NCHS-style screen is a research assessment, not official publication
clearance. These binomial screening criteria do not apply to the paired difference.

Additional missing-data diagnostics are 36 age-group x sex x race/ethnicity response
cells and a paired-change missing-group stress test. Response-cell targets come from all
examined adults; their totals are treated as fixed for the sensitivity intervals. The
analysis assumes exchangeability within cells and does not identify nonignorable
nonresponse. Worst-case paired-change bounds are identification bounds, not confidence
intervals. These additions followed inspection of pilot results and are not
prospectively preregistered.

See report/robustness_reliability_review.md and docs/robustness_methods.md. Rerun
with scripts/validation/run_validation.ps1 -ReviewRobustness.

## Interpretation of existing result files

Outcome keys such as `raw_above_30` are retained for compatibility; they mean
**at or above 30 mg/g**, as specified in the code. The primary sample and
historical reference are analysed separately. Historical keys such as
`2017-2020` refer to January 2017–March 2020, not a complete 2020 cycle.

The seven QC checks are exact unweighted counts. The 216 numerical
comparisons use the same estimands and interval convention in Python and R;
agreement verifies implementation under this protocol, not the suitability
of every scientific assumption. Both implementations were developed in the
same project, so this is software cross-validation rather than an independent
external scientific audit.

## Data preparation implementation

The Python workflow uses SQLite for demographics-first joins, eligibility flags, UACR and assay conversion, and descriptive aggregates. All positive-weight MEC records remain available for domain estimation. R independently reconstructs the analysis from XPT files. See the [SQL data pipeline](sql_data_pipeline.md) for the query map and verification; the estimand and survey methods are unchanged.
