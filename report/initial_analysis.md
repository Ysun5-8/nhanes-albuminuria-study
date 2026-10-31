# Cohort audit and initial paired survey analysis

Aggregate results reproduced from cached CDC XPT files.

## Cohort flow

| Stage | August 2021-August 2023 | 2017-March 2020 reference |
|---|---:|---:|
| Adults >=20 in demographics | 7,809 | 9,232 |
| Interview only, zero MEC weight | 1,745 | 688 |
| Positive MEC weight / examined adults | 6,064 | 8,544 |
| Valid urine albumin and creatinine | 5,910 | 8,319 |
| Missing or invalid urine results among examined adults | 154 | 225 |
| Missing or invalid, unweighted % of examined adults | 2.54% | 2.63% |
| Missing or invalid, MEC-weighted % of examined adults | 2.60% | 1.87% |

All 154 recent-cycle missing cases lack both analytes. There are no nonmissing
invalid concentrations, missing design fields among eligible adults, or examined
adults lacking a laboratory-file row. Recent-cycle age-group missingness is
2.25% (20-39), 1.90% (40-59), and 3.10% (60+), unweighted. Detailed demographic
breakdowns are in `outputs/tables/mec_missingness_audit.json`.

The earlier 1,899 count combined 1,745 interview-only adults and 154 examined
adults with missing results. It therefore overstates urine item nonresponse
among examined adults. The current audit uses the examination denominator.

The XPT reader decoded stored zero as exactly `16**-65` (about 5.4e-79), which
wrongly passes a positive-weight check. The loader now restores that exact value
to zero. Examination status confirms the corrected weight eligibility. The change
also restores zero-valued detection flags; genuine small concentrations are kept.

## Paired survey results

Design: all 8,860 positive-MEC-weight participants, 15 strata, 30 PSUs, 15 design
degrees of freedom. Analysis domain: 5,910 adults with complete valid urine data.
Taylor linearised variance with two-sided t Wald 95% confidence intervals.

| Outcome | Weighted estimate | Design-adjusted 95% CI |
|---|---:|---:|
| Raw UACR >=30 mg/g | 10.35% | 9.36-11.35% |
| Harmonised UACR >=30 mg/g | 11.42% | 10.25-12.59% |
| Paired change, harmonised minus raw | +1.06 percentage points | +0.68 to +1.45 |
| Any reclassification | 1.23% | 0.85-1.61% |
| Below to at/above threshold | 1.15% | 0.77-1.52% |
| At/above to below threshold | 0.084% | 0.018-0.151% |

Unweighted pilot remains 721 raw positives, 786 harmonised positives, 71 upward
and six downward reclassifications (77 total). These counts are distinct from
weighted population proportions.

## Sensitivities and interpretation

- Excluding below-detection observations or negative bridge predictions leaves
  5,484 adults and yields a +1.15 percentage-point paired change. These exclusions change the
  analysis domain.
- Omitting zero-clipping leaves the threshold classification results unchanged.
- Strict >30 yields +1.07 percentage points; using CDC rounded raw URDACT yields
  +1.06 percentage points, unchanged from primary at displayed precision.
- Assigning all missing adult urine outcomes negative or positive gives raw
  prevalence bounds of 10.08-12.69%, and harmonised bounds of 11.12-13.72% among
  all examined adults. These extreme bounds have no confidence intervals and
  do not estimate likely missing outcomes.

These are complete-data survey estimates using released weights without item
nonresponse adjustment. National interpretation depends on residual urine
nonresponse being ignorable. Confidence intervals include sampling uncertainty
but condition on fixed bridge coefficients. The subsequent [reliability review](robustness_reliability_review.md) assesses
rare directional changes against the NCHS proportion framework. Single specimens do not establish CKD.

## Validation and files

At the initial analysis stage, twelve tests passed, including hand-calculated domain variance with an empty-domain
PSU, zero-decoding regression, missingness denominator, and paired-outcome checks.
Both cycles' original feasibility counts reproduce. The variance implementation
has now been independently compared against R's survey package (version 4.5), an
established survey-analysis implementation. All 216 checks passed across the primary analysis and five sensitivities. See report/r_survey_validation.md.

- `docs/protocol.md`: conventions, estimands, variance formula and source links.
- `scripts/pilot/audit_cohort.py`: demographics-first flow and missingness.
- `scripts/paired_analysis.py`: paired survey estimation and sensitivities.
- `outputs/tables/paired_survey_analysis.json`: full precision estimates and CIs.

CDC sources and reproduction commands are listed in the protocol. This is an
initial analysis following the exploratory pilot, not a preregistered confirmatory study.
