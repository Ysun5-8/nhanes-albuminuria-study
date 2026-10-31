# Calibration and validation stability

This follow-up was specified after the initial model comparison. Model settings
and predictors remain fixed. Logistic regression is the primary model because
its structure is easier to inspect; gradient boosting remains a comparison.
Neither model is selected or tuned using the follow-up results.

## Calibration

For seed 42, weighted mean predictions are compared with weighted observed
proportions in the original probability bands: 0–5%, 5–10%, 10–20%, 20–40%, 40–60% and
60–100%. The final band includes 100%. Each participant contributes one
out-of-fold probability. Raw and converted outcomes use the same probabilities
and bin membership. Counts accompany the plot because high-probability bands
contain few participants.

Overall calibration is summarised by mean predicted probability minus observed
prevalence, in percentage points. Positive values indicate overprediction and
negative values underprediction. This overall gap can hide errors within bands.
Brier score measures probability error, not calibration alone. No post-hoc
recalibration is fitted to the evaluation outcomes.

## Split stability

Five-fold grouped validation is repeated with seeds 42, 101, 202, 303 and 404.
All preprocessing and model fitting are repeated within the training folds.
PSU groups stay intact. Outputs include every run and the minimum and maximum
weighted ROC-AUC, average precision, Brier score and overall calibration gap. These
ranges describe sensitivity to the split; they are not confidence intervals.

## Conditional resampling intervals

The analysis uses 1,000 resamples with seed 2026, keeping the seed-42 predictions fixed. The
positive-weight survey design has two public-use PSUs in each of 15 strata.
Within each stratum, one of its two PSUs is selected with equal probability.
Its examination weights are doubled and the other PSU receives zero weight.
The same selection applies to both labels and both models. This is the two-PSU case of sampling
n−1 PSUs in the Rao–Wu rescaled bootstrap, under a with-replacement first-stage
approximation and without a finite population correction.

Resampling groups are built from the full positive-weight MEC design and applied
to complete-urine adults. A stratum without exactly two PSUs stops the analysis.
For each metric and paired contrast, the 2.5th and 97.5th percentiles form an
approximate 95% conditional resampling interval. Contrasts are calculated within
each resample before percentiles are taken. Empty calibration bins are omitted
from that resample's estimates; valid-resample counts are reported and intervals
are suppressed if fewer than 950 are valid.

These intervals describe sensitivity to the survey-group composition conditional
on the realised predictions. They do not refit models and are not full confidence
intervals for the learning procedure. Out-of-fold predictions share overlapping
training data; this dependence and training uncertainty are not captured by the
conditional intervals. The split ranges provide a separate stability check but
do not fill that inferential gap. Public-use design variables are an approximation
to the confidential sampling design. Missing outcomes and uncertainty in the
assay bridge remain outside both assessments. No external validation or clinical
performance claim is made.

## References

- [Survey package: bootstrap weights](https://r-survey.r-forge.r-project.org/pkgdown/docs/reference/bootweights.html).
- [Statistics Canada: rescaled bootstrap for stratified multistage sampling](https://www150.statcan.gc.ca/n1/pub/12-001-x/2009002/article/11044-eng.pdf).
- [Scikit-learn: probability calibration](https://scikit-learn.org/stable/modules/calibration).

## Reproduction

Run `scripts/ml/run_ml.ps1 -Validation` after installing the optional ML packages.
The command recalculates predictions; no participant-level prediction file is
saved. It writes `ml_split_results.csv`, `ml_split_ranges.csv`,
`ml_conditional_intervals.csv`, `ml_calibration_intervals.csv` and
`ml_validation_status.json` under `outputs/tables/`, and replaces
`report/ml_validation.md`. The R figure script reads those aggregates:

```powershell
Rscript scripts/visualisation/create_ml_calibration.R .
```

The figure script writes `outputs/figures/figure_3_ml_calibration.png` and its
vector PDF version. Methods and display conventions are in the
[figure legend](../report/ml_figure_legend.md).
