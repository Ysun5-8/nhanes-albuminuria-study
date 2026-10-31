# Figure 3. Calibration under raw and converted assay definitions

Panels A and B show logistic regression and gradient boosting, respectively.
Points compare MEC-weighted mean predicted probabilities with weighted observed
proportions in six fixed prediction bands (0–5%, 5–10%, 10–20%, 20–40%, 40–60%
and 60–100%). Bands include their lower boundary; the last also includes 100%.
Lines connect bin summaries and are not fitted calibration curves. The dashed
grey line represents equality of predicted and observed probabilities.

Both models were trained on raw UACR >=30 mg/g. Each of 5,910 adults received
one held-out prediction from seed-42 five-fold validation, keeping public-use
PSU groups intact. Raw and converted outcomes are evaluated using identical
predictions and bin membership. Lower panels give unweighted participant counts,
shared by the two outcome definitions within each model. Sparse high-probability
bins limit calibration interpretation.

Vertical lines are approximate 95% conditional resampling intervals from 1,000
Rao–Wu two-PSU resamples within survey strata. Predictions and bin membership
remain fixed. Intervals describe survey-group composition uncertainty conditional
on those predictions; they do not include model-refitting uncertainty, dependence
from overlapping training sets, assay-bridge uncertainty or missing-outcome bias.
They are not full confidence intervals for predictive performance. No clinical
validation is implied. See [methods](../docs/ml_validation_methods.md).
