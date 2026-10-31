# Model calibration and validation stability

The follow-up retained the original predictors and fixed model settings. Logistic regression was the primary model; gradient boosting provided a comparison. All 5,910 complete-urine adults were retained.

## Calibration

Figure 3 compares weighted observed proportions with mean out-of-fold predictions. The overall prediction-minus-observation gap is shown below; negative values indicate underprediction. These averages can conceal errors within probability bands.

| Model | Assay definition | Overall gap (percentage points) | 95% conditional interval |
|---|---|---:|---:|
| Logistic regression | Raw | +0.05 | -0.72 to +0.69 |
| Logistic regression | Converted | -1.02 | -1.92 to -0.24 |
| Gradient boosting | Raw | -0.08 | -0.87 to +0.60 |
| Gradient boosting | Converted | -1.14 | -2.09 to -0.33 |

![Figure 3. Calibration under both assay definitions](../outputs/figures/figure_3_ml_calibration.png)

[Figure legend](ml_figure_legend.md). The highest probability band contains only 39 participants for logistic regression and 23 for gradient boosting. These sparse bands limit detailed calibration interpretation.

## Validation stability

Five prespecified seeds changed the grouped fold assignments. Models and preprocessing were refitted for every run. The ranges below describe split sensitivity; they are not confidence intervals.

| Model | Assay definition | ROC-AUC range | Brier score range |
|---|---|---:|---:|
| Logistic regression | Raw | 0.740 to 0.744 | 0.0825 to 0.0828 |
| Logistic regression | Converted | 0.728 to 0.733 | 0.0898 to 0.0902 |
| Gradient boosting | Raw | 0.761 to 0.765 | 0.0816 to 0.0820 |
| Gradient boosting | Converted | 0.749 to 0.753 | 0.0891 to 0.0893 |

## Paired changes after assay conversion

| Model | ROC-AUC change | 95% conditional interval | Brier score change | 95% conditional interval |
|---|---:|---:|---:|---:|
| Logistic regression | -0.0118 | -0.0254 to +0.0010 | +0.0073 | +0.0048 to +0.0098 |
| Gradient boosting | -0.0131 | -0.0265 to -0.0004 | +0.0073 | +0.0049 to +0.0098 |

## Interpretation and limitations

The models were trained against the raw labels. Changing the assay definition changes the outcomes against which the same probabilities are judged. It does not improve or worsen the fitted model itself. Calibration results are specific to the outcome definition used for evaluation.

Conditional intervals use 1,000 within-stratum PSU resamples with fixed seed-42 predictions. They reflect changes in survey-group composition, not the full uncertainty of model development. Shared training data across out-of-fold predictions, model-fitting variability, assay-bridge uncertainty and missing-outcome bias are not included. The separate split ranges do not turn these conditional intervals into full confidence intervals. No claim of model superiority or clinical readiness follows from this analysis.

All weighted metrics, model contrasts, calibration counts and valid-resample counts are available in the aggregate tables. [Methods and sources](../docs/ml_validation_methods.md) describe the resampling and [reproduction instructions](../docs/ml_reproduction.md) give the commands.
