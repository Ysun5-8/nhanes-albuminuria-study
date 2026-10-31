"""Compare held-out model predictions under the two assay definitions."""
import json
import platform
import warnings
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from scripts.ml.prepare_data import NUMERIC, CATEGORICAL, prepare_ml, audit
from scripts.pilot.check_feasibility import OUTPUT, ROOT


def models():
    numeric = Pipeline([('impute', SimpleImputer(strategy='median', add_indicator=True)),
                        ('scale', StandardScaler())])
    preprocess = ColumnTransformer([
        ('numeric', numeric, NUMERIC),
        ('categorical', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL)])
    estimators = {
        'logistic': LogisticRegression(C=1.0, max_iter=1000),
        'gradient_boosting': HistGradientBoostingClassifier(
            max_iter=100, learning_rate=0.05, max_leaf_nodes=7,
            min_samples_leaf=30, l2_regularization=1.0,
            early_stopping=False, random_state=42),
    }
    return {name: Pipeline([('prepare', clone(preprocess)), ('model', estimator)])
            for name, estimator in estimators.items()}


def metrics(y, p, weights):
    return {'roc_auc': float(roc_auc_score(y, p, sample_weight=weights)),
            'average_precision': float(average_precision_score(y, p, sample_weight=weights)),
            'brier': float(brier_score_loss(y, p, sample_weight=weights)),
            'log_loss': float(log_loss(y, p, sample_weight=weights)),
            'mean_prediction': float(np.average(p, weights=weights)),
            'prevalence': float(np.average(y, weights=weights))}


def predict_oof(frame, seed=42):
    # These are the only columns that enter either model.
    X = frame[NUMERIC + CATEGORICAL]
    y = frame.raw_label.to_numpy(dtype=int)
    w = frame.WTMEC2YR.to_numpy(dtype=float)
    groups = frame.SDMVSTRA.astype(str) + ':' + frame.SDMVPSU.astype(str)
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    predictions = {name: np.full(len(frame), np.nan) for name in ['baseline', 'logistic', 'gradient_boosting']}
    seen = np.zeros(len(frame), dtype=int)
    folds = []
    for fold, (train, test) in enumerate(splitter.split(X, y, groups), 1):
        if set(groups.iloc[train]) & set(groups.iloc[test]):
            raise ValueError('A PSU appears in both training and evaluation data')
        for label in ('raw_label', 'converted_label'):
            if frame.iloc[train][label].nunique() != 2 or frame.iloc[test][label].nunique() != 2:
                raise ValueError(f'Fold {fold} lacks one outcome class')
        seen[test] += 1
        predictions['baseline'][test] = np.average(y[train], weights=w[train])
        for name, model in models().items():
            # Imputation and scaling are fitted inside this training fold.
            with warnings.catch_warnings():
                warnings.simplefilter('error', ConvergenceWarning)
                model.fit(X.iloc[train], y[train], model__sample_weight=w[train] / w[train].mean())
            predictions[name][test] = model.predict_proba(X.iloc[test])[:, 1]
        folds.append({'fold': fold, 'n_train': len(train), 'n_test': len(test),
                      'n_test_psus': int(groups.iloc[test].nunique()),
                      'n_raw_positive_test': int(y[test].sum()),
                      'n_converted_positive_test': int(frame.iloc[test].converted_label.sum()),
                      'psu_overlap': 0})
    if not np.all(seen == 1) or any(not np.isfinite(p).all() for p in predictions.values()):
        raise ValueError('Incomplete out-of-fold predictions')
    return predictions, folds


def calibration(frame, predictions):
    rows = []
    edges = [0., .05, .10, .20, .40, .60, 1.]
    for name, p in predictions.items():
        for low, high in zip(edges[:-1], edges[1:]):
            mask = (p >= low) & ((p < high) if high < 1 else (p <= high))
            if not mask.any():
                continue
            part = frame.loc[mask]
            w = part.WTMEC2YR.to_numpy()
            rows.append({'model': name, 'bin_lower': low, 'bin_upper': high,
                         'n': int(mask.sum()), 'raw_cases': int(part.raw_label.sum()),
                         'converted_cases': int(part.converted_label.sum()),
                         'mean_prediction': float(np.average(p[mask], weights=w)),
                         'raw_observed': float(np.average(part.raw_label, weights=w)),
                         'converted_observed': float(np.average(part.converted_label, weights=w))})
    return pd.DataFrame(rows)


def main():
    frame = prepare_ml()
    audit(frame)
    predictions, folds = predict_oof(frame)
    rows = []
    for name, p in predictions.items():
        for weighting, w in [('mec_weighted', frame.WTMEC2YR.to_numpy()),
                             ('unweighted', np.ones(len(frame)))]:
            for label in ('raw_label', 'converted_label'):
                rows.append({'model': name, 'weighting': weighting, 'outcome': label,
                             **metrics(frame[label].to_numpy(dtype=int), p, w)})
    results = pd.DataFrame(rows)
    results.to_csv(OUTPUT / 'ml_performance.csv', index=False)
    calibration(frame, predictions).to_csv(OUTPUT / 'ml_calibration.csv', index=False)
    pd.DataFrame(folds).to_csv(OUTPUT / 'ml_folds.csv', index=False)
    deltas = []
    for (name, weighting), part in results.groupby(['model', 'weighting']):
        part = part.set_index('outcome')
        deltas.append({'model': name, 'weighting': weighting,
                       **{key: float(part.loc['converted_label', key] - part.loc['raw_label', key])
                          for key in ('roc_auc', 'average_precision', 'brier', 'log_loss', 'prevalence')}})
    pd.DataFrame(deltas).to_csv(OUTPUT / 'ml_assay_comparison.csv', index=False)
    status = {'n': len(frame), 'folds': 5, 'seed': 42,
              'training_outcome': 'raw UACR >=30 mg/g',
              'predictors': NUMERIC + CATEGORICAL,
              'validation': 'out-of-fold; grouped by joint survey stratum/PSU',
              'each_participant_evaluated_once': True, 'no_psu_overlap': True,
              'inference': 'exploratory point estimates; no confidence intervals or external validation',
              'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                           'pandas': pd.__version__, 'scipy': scipy.__version__, 'scikit_learn': sklearn.__version__}}
    (OUTPUT / 'ml_run_status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    lines = ['# Initial ML comparison', '',
             'Models used age, recorded sex, BMI, blood pressure, diabetes history and smoking to classify elevated single-specimen UACR. All 5,910 adults remained in the cohort; missing predictors were handled within training folds.', '',
             'Each participant was evaluated once in five-fold validation, with public-use PSU groups kept together. Models were trained on raw classifications. The same held-out probabilities were then evaluated against converted classifications.', '',
             '## MEC-weighted performance', '',
             '| Model | Outcome | ROC-AUC | Average precision | Brier score |',
             '|---|---|---:|---:|---:|']
    for row in rows:
        if row['weighting'] == 'mec_weighted':
            lines.append(f"| {row['model']} | {row['outcome']} | {row['roc_auc']:.3f} | {row['average_precision']:.3f} | {row['brier']:.4f} |")
    lines += ['', 'Follow-up: [calibration and validation stability](ml_validation.md).', '', '## Interpretation', '',
              'Higher ROC-AUC and average precision indicate better discrimination; lower Brier scores indicate smaller probability errors. Average precision also depends on outcome prevalence. A change after conversion reflects a different outcome definition, not an improvement in the fitted model.', '',
              'These are exploratory internal-validation point estimates. They do not establish clinical usefulness, population performance with design-based uncertainty, or that one model is superior. The assay bridge is treated as fixed, urine nonresponse remains unresolved, and there is no external validation. Calibration-bin counts and weighted observed rates are saved separately; sparse bins limit calibration interpretation.', '',
              'The baseline uses the training-fold weighted prevalence. Its probabilities vary across folds, so its pooled ROC-AUC need not equal 0.5.', '',
              'See the [analysis plan](../docs/ml_analysis_plan.md) and [reproduction instructions](../docs/ml_reproduction.md). Aggregate outputs include unweighted sensitivities, fold counts, paired metric changes and calibration summaries. No participant-level predictions or fitted deployment model are saved.']
    (ROOT / 'report/ml_initial_results.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(results.to_string(index=False))


if __name__ == '__main__':
    main()
