"""Assess calibration, split stability and conditional survey-group uncertainty."""
import json
import numpy as np
import pandas as pd
from scripts.ml.prepare_data import prepare_ml
from scripts.ml.run_models import predict_oof, metrics, calibration
from scripts.pilot.audit_cohort import join_cycle
from scripts.pilot.check_feasibility import OUTPUT, ROOT

SEEDS = [42, 101, 202, 303, 404]
MODEL_NAMES = ['logistic', 'gradient_boosting']
LABELS = ['raw_label', 'converted_label']
METRICS = ['roc_auc', 'average_precision', 'brier', 'calibration_gap_pp']


def evaluate(y, p, w):
    result = metrics(y, p, w)
    result['calibration_gap_pp'] = 100 * (result['mean_prediction'] - result['prevalence'])
    return {key: result[key] for key in METRICS}


def design_codes(full, frame):
    """Map adults to the two PSUs in each full-design stratum."""
    design = full.loc[full.positive_mec, ['SDMVSTRA', 'SDMVPSU']].drop_duplicates()
    if design.isna().any().any():
        raise ValueError('Missing survey design fields')
    strata = sorted(design.SDMVSTRA.unique())
    mapping = {}
    for h, stratum in enumerate(strata):
        psus = sorted(design.loc[design.SDMVSTRA.eq(stratum), 'SDMVPSU'])
        if len(psus) != 2:
            raise ValueError('Resampling requires two PSUs per stratum')
        mapping.update({(stratum, psu): (h, j) for j, psu in enumerate(psus)})
    codes = np.array([mapping[(h, j)] for h, j in zip(frame.SDMVSTRA, frame.SDMVPSU)])
    return codes[:, 0], codes[:, 1], len(strata)


def replicate_weights(weights, stratum_codes, psu_codes, selected):
    return weights * 2.0 * (psu_codes == selected[stratum_codes])


def contrasts(values):
    rows = {}
    for model in MODEL_NAMES:
        for label in LABELS:
            for metric in METRICS:
                rows[(model, label, metric)] = values[(model, label)][metric]
        for metric in METRICS:
            rows[(model, 'converted_minus_raw', metric)] = (
                values[(model, 'converted_label')][metric] - values[(model, 'raw_label')][metric])
    for label in LABELS:
        for metric in METRICS:
            rows[('boosting_minus_logistic', label, metric)] = (
                values[('gradient_boosting', label)][metric] - values[('logistic', label)][metric])
    return rows


def conditional_intervals(frame, predictions, full, replicates=1000):
    weights = frame.WTMEC2YR.to_numpy()
    h, j, n_strata = design_codes(full, frame)
    labels = {label: frame[label].to_numpy(dtype=int) for label in LABELS}
    base = contrasts({(model, label): evaluate(labels[label], predictions[model], weights)
                      for model in MODEL_NAMES for label in LABELS})
    draws = {key: [] for key in base}
    bins = calibration(frame, {name: predictions[name] for name in MODEL_NAMES})
    bin_masks = [(predictions[row.model] >= row.bin_lower) &
                 ((predictions[row.model] < row.bin_upper) if row.bin_upper < 1
                  else (predictions[row.model] <= 1)) for row in bins.itertuples()]
    bin_draws = {(i, label): [] for i in range(len(bins)) for label in LABELS}
    rng = np.random.default_rng(2026)
    for _ in range(replicates):
        w = replicate_weights(weights, h, j, rng.integers(0, 2, n_strata))
        values = contrasts({(model, label): evaluate(labels[label], predictions[model], w)
                            for model in MODEL_NAMES for label in LABELS})
        for key, value in values.items():
            if not np.isfinite(value):
                raise ValueError('Undefined resampled metric')
            draws[key].append(value)
        for i, mask in enumerate(bin_masks):
            if w[mask].sum() > 0:
                for label in LABELS:
                    bin_draws[(i, label)].append(np.average(labels[label][mask], weights=w[mask]))
    rows = []
    for (model, label, metric), values in draws.items():
        low, high = np.quantile(values, [.025, .975])
        rows.append({'model': model, 'outcome': label, 'metric': metric,
                     'estimate': base[(model, label, metric)], 'lower': low, 'upper': high,
                     'valid_replicates': len(values)})
    for label, prefix in [('raw_label', 'raw'), ('converted_label', 'converted')]:
        for bound, q in [('lower', .025), ('upper', .975)]:
            bins[f'{prefix}_{bound}'] = [np.quantile(bin_draws[(i, label)], q)
                if len(bin_draws[(i, label)]) >= .95 * replicates else np.nan for i in range(len(bins))]
        bins[f'{prefix}_valid_replicates'] = [len(bin_draws[(i, label)]) for i in range(len(bins))]
    return pd.DataFrame(rows), bins, n_strata


def write_report(intervals, ranges):
    names = {'logistic': 'Logistic regression', 'gradient_boosting': 'Gradient boosting'}
    lines = ['# Model calibration and validation stability', '',
             'The follow-up retained the original predictors and fixed model settings. Logistic regression was the primary model; gradient boosting provided a comparison. All 5,910 complete-urine adults were retained.', '',
             '## Calibration', '',
             'Figure 3 compares weighted observed proportions with mean out-of-fold predictions. The overall prediction-minus-observation gap is shown below; negative values indicate underprediction. These averages can conceal errors within probability bands.', '',
             '| Model | Assay definition | Overall gap (percentage points) | 95% conditional interval |',
             '|---|---|---:|---:|']
    for model in MODEL_NAMES:
        for label in LABELS:
            row = intervals.query('model == @model and outcome == @label and metric == "calibration_gap_pp"').iloc[0]
            lines.append(f"| {names[model]} | {'Raw' if label == 'raw_label' else 'Converted'} | {row.estimate:+.2f} | {row.lower:+.2f} to {row.upper:+.2f} |")
    lines += ['', '![Figure 3. Calibration under both assay definitions](../outputs/figures/figure_3_ml_calibration.png)', '',
              '[Figure legend](ml_figure_legend.md). The highest probability band contains only 39 participants for logistic regression and 23 for gradient boosting. These sparse bands limit detailed calibration interpretation.', '',
              '## Validation stability', '',
              'Five prespecified seeds changed the grouped fold assignments. Models and preprocessing were refitted for every run. The ranges below describe split sensitivity; they are not confidence intervals.', '',
              '| Model | Assay definition | ROC-AUC range | Brier score range |',
              '|---|---|---:|---:|']
    for model in MODEL_NAMES:
        for label in LABELS:
            part = ranges.query('model == @model and outcome == @label').set_index('metric')
            lines.append(f"| {names[model]} | {'Raw' if label == 'raw_label' else 'Converted'} | {part.loc['roc_auc','minimum']:.3f} to {part.loc['roc_auc','maximum']:.3f} | {part.loc['brier','minimum']:.4f} to {part.loc['brier','maximum']:.4f} |")
    lines += ['', '## Paired changes after assay conversion', '',
              '| Model | ROC-AUC change | 95% conditional interval | Brier score change | 95% conditional interval |',
              '|---|---:|---:|---:|---:|']
    for model in MODEL_NAMES:
        part = intervals.query('model == @model and outcome == "converted_minus_raw"').set_index('metric')
        a, b = part.loc['roc_auc'], part.loc['brier']
        lines.append(f"| {names[model]} | {a.estimate:+.4f} | {a.lower:+.4f} to {a.upper:+.4f} | {b.estimate:+.4f} | {b.lower:+.4f} to {b.upper:+.4f} |")
    lines += ['', '## Interpretation and limitations', '',
              'The models were trained against the raw labels. Changing the assay definition changes the outcomes against which the same probabilities are judged. It does not improve or worsen the fitted model itself. Calibration results are specific to the outcome definition used for evaluation.', '',
              'Conditional intervals use 1,000 within-stratum PSU resamples with fixed seed-42 predictions. They reflect changes in survey-group composition, not the full uncertainty of model development. Shared training data across out-of-fold predictions, model-fitting variability, assay-bridge uncertainty and missing-outcome bias are not included. The separate split ranges do not turn these conditional intervals into full confidence intervals. No claim of model superiority or clinical readiness follows from this analysis.', '',
              'All weighted metrics, model contrasts, calibration counts and valid-resample counts are available in the aggregate tables. [Methods and sources](../docs/ml_validation_methods.md) describe the resampling and [reproduction instructions](../docs/ml_reproduction.md) give the commands.']
    (ROOT / 'report/ml_validation.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    frame = prepare_ml()
    full = join_cycle('2021-2023')
    rows = []
    first = None
    for seed in SEEDS:
        predictions, _ = predict_oof(frame, seed=seed)
        if seed == 42:
            first = predictions
        for model in MODEL_NAMES:
            for label in LABELS:
                values = evaluate(frame[label].to_numpy(dtype=int), predictions[model], frame.WTMEC2YR.to_numpy())
                rows.extend({'seed': seed, 'model': model, 'outcome': label, 'metric': metric, 'value': value}
                            for metric, value in values.items())
        print(f'Completed grouped validation: seed {seed}', flush=True)
    results = pd.DataFrame(rows)
    original = pd.read_csv(OUTPUT / 'ml_performance.csv')
    for row in results.loc[results.seed.eq(42)].itertuples():
        old = original.loc[original.model.eq(row.model) & original.outcome.eq(row.outcome)
                           & original.weighting.eq('mec_weighted')].iloc[0]
        expected = (100 * (old.mean_prediction - old.prevalence)
                    if row.metric == 'calibration_gap_pp' else old[row.metric])
        if not np.isclose(row.value, expected, atol=1e-12, rtol=1e-12):
            raise ValueError('Seed-42 results differ from the initial run')
    ranges = results.groupby(['model', 'outcome', 'metric']).value.agg(minimum='min', maximum='max').reset_index()
    intervals, bins, n_strata = conditional_intervals(frame, first, full)
    results.to_csv(OUTPUT / 'ml_split_results.csv', index=False)
    ranges.to_csv(OUTPUT / 'ml_split_ranges.csv', index=False)
    intervals.to_csv(OUTPUT / 'ml_conditional_intervals.csv', index=False)
    bins.to_csv(OUTPUT / 'ml_calibration_intervals.csv', index=False)
    status = {'n_adults': len(frame), 'split_seeds': SEEDS, 'folds_per_seed': 5,
              'n_full_design_strata': n_strata, 'psus_per_stratum': 2,
              'resamples': 1000, 'resampling_seed': 2026,
              'conditional_on_seed_42_predictions': True, 'models_refitted_in_resamples': False,
              'initial_run_agreement': True,
              'all_metric_resamples_valid': bool(intervals.valid_replicates.eq(1000).all()),
              'minimum_valid_bin_resamples': int(bins.raw_valid_replicates.min()),
              'interpretation': 'Conditional resampling intervals; split ranges are not confidence intervals.'}
    (OUTPUT / 'ml_validation_status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    write_report(intervals, ranges)
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
