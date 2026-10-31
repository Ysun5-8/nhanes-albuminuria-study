# Assay conversion and model performance

## Question

Does changing the urine albumin assay scale change the measured performance of a
model for elevated single-specimen UACR? Predictions use measurements that could
be available before the urine result. This is classification at the same visit,
not prediction of future kidney disease or a diagnostic tool.

This plan was written before the first model fit. The original harmonisation
results were already known, so the extension remains exploratory.

## Inputs

The planned cohort is the existing complete-urine adult sample in August
2021–August 2023. SQL left joins on SEQN add the following files without removing
participants with missing predictors. Input checks cover unique keys and
unmatched records.

| Predictor | Source | Coding |
|---|---|---|
| Age | DEMO_L: RIDAGEYR | Released age; older ages are top-coded |
| Recorded sex | DEMO_L: RIAGENDR | Categorical |
| BMI | BMX_L: BMXBMI | Continuous |
| Systolic and diastolic pressure | BPXO_L | Mean of available positive readings among the three measurements; missing if none |
| Diabetes history | DIQ_L: DIQ010 | Yes, no, borderline; refused/unknown/missing kept missing |
| Smoking | SMQ_L: SMQ020, SMQ040 | Never (<100 lifetime cigarettes), former, current; account for the follow-up skip pattern |

Predictors exclude urine analytes, UACR, detection flags, converted values, survey
weights, strata, PSUs and SEQN. Weights are used for fitting and evaluation;
PSUs are used for data splitting. Outcomes are not imputed.

Codebooks: [BMI](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BMX_L.htm),
[blood pressure](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BPXO_L.htm),
[diabetes](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DIQ_L.htm),
[smoking](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/SMQ_L.htm).

## First comparison

The training outcome is raw UACR >=30 mg/g. The comparison includes a training-fold weighted-prevalence
baseline, L2 logistic regression (C=1, max_iter=1000), and histogram gradient
boosting (100 iterations, learning rate 0.05, seven leaves, minimum 30 samples
per leaf, L2=1, early stopping disabled). These settings are fixed for the first
run; there is no search for the best test score.

Five folds are grouped by the joint SDMVSTRA/SDMVPSU identifier, using
StratifiedGroupKFold and seed 42. Every participant receives one prediction from
a model fitted without that participant or their public-use PSU group. Each
training and evaluation fold is checked for both outcome classes. These masked survey groups
are not an external geographic validation sample.

Within each training fold, missing numeric predictors are replaced with
unweighted training medians, with missingness indicators added before
standardisation. Categorical predictors use an explicit missing category and
one-hot encoding learned in that fold. The tree model uses the same prepared inputs. No preprocessing is
fitted on the evaluation fold. Training MEC weights are normalised to mean one
before fitting; evaluation uses the original MEC weights. Cases are not oversampled.

The same out-of-fold probabilities are evaluated against raw and converted
labels using weighted ROC-AUC, average precision, Brier score, log loss, mean
predicted probability and observed prevalence. Outputs also include unweighted
metrics as a sensitivity, weighted calibration summaries in fixed probability
bins and converted-minus-raw metric contrasts within each model. Average precision depends on prevalence,
so a change alone is not evidence of better ranking.

## Interpretation

This first run reports internal-validation point estimates, without confidence
intervals or model-superiority claims. Grouped folds and weights do not by
themselves provide design-based uncertainty or address urine nonresponse.
Calibration bins are descriptive and may be sparse. A fold-specific baseline
can have pooled AUC different from 0.5 because its prediction changes by fold.

Any later tuning needs inner training folds; choosing settings from these results
would make this first run part of model development. External validation,
resampling that accounts for the survey design and training variability, and
clinical usefulness are beyond this initial comparison. The original survey
report remains the primary analysis. Only aggregate outputs are saved.

The subsequent [calibration and stability assessment](ml_validation_methods.md)
retains these fixed model settings. It adds conditional resampling intervals and
split-sensitivity ranges; neither is a full confidence interval for the learning
procedure.
