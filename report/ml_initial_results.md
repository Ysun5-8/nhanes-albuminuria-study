# Initial ML comparison

Models used age, recorded sex, BMI, blood pressure, diabetes history and smoking to classify elevated single-specimen UACR. All 5,910 adults remained in the cohort; missing predictors were handled within training folds.

Each participant was evaluated once in five-fold validation, with public-use PSU groups kept together. Models were trained on raw classifications. The same held-out probabilities were then evaluated against converted classifications.

## MEC-weighted performance

| Model | Outcome | ROC-AUC | Average precision | Brier score |
|---|---|---:|---:|---:|
| baseline | raw_label | 0.463 | 0.096 | 0.0929 |
| baseline | converted_label | 0.458 | 0.105 | 0.1014 |
| logistic | raw_label | 0.741 | 0.315 | 0.0827 |
| logistic | converted_label | 0.729 | 0.333 | 0.0900 |
| gradient_boosting | raw_label | 0.762 | 0.321 | 0.0817 |
| gradient_boosting | converted_label | 0.749 | 0.337 | 0.0891 |

Follow-up: [calibration and validation stability](ml_validation.md).

## Interpretation

Higher ROC-AUC and average precision indicate better discrimination; lower Brier scores indicate smaller probability errors. Average precision also depends on outcome prevalence. A change after conversion reflects a different outcome definition, not an improvement in the fitted model.

These are exploratory internal-validation point estimates. They do not establish clinical usefulness, population performance with design-based uncertainty, or that one model is superior. The assay bridge is treated as fixed, urine nonresponse remains unresolved, and there is no external validation. Calibration-bin counts and weighted observed rates are saved separately; sparse bins limit calibration interpretation.

The baseline uses the training-fold weighted prevalence. Its probabilities vary across folds, so its pooled ROC-AUC need not equal 0.5.

See the [analysis plan](../docs/ml_analysis_plan.md) and [reproduction instructions](../docs/ml_reproduction.md). Aggregate outputs include unweighted sensitivities, fold counts, paired metric changes and calibration summaries. No participant-level predictions or fitted deployment model are saved.
