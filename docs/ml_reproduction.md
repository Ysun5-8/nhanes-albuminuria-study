# Reproducing the initial ML comparison

First set up the existing Python analysis environment using
[reproduction.md](reproduction.md). The validated ML run uses Python 3.12.10,
NumPy 2.5.4, pandas 2.3.3 and SciPy 1.18.1. Additional package versions are in
[ml-requirements.txt](ml-requirements.txt).

Install the optional packages into a separate local folder. The `--no-deps`
option relies on the existing scientific packages and the complete list of
additional packages in the requirements file; it avoids upgrading the original
analysis environment.

```powershell
.\.venv\Scripts\python.exe -m pip install --target .ml-library --no-deps -r docs/ml-requirements.txt
.\scripts\ml\run_ml.ps1 -Test
.\scripts\ml\run_ml.ps1
.\scripts\ml\run_ml.ps1 -Validation
```

Run installation once on a fresh setup. The launcher adds `.ml-library` to the
module search path for the command and restores the previous setting afterwards.
The library folder is excluded from Git.

The loader downloads missing predictor files from CDC into `data/raw/`:
`BMX_L.xpt`, `BPXO_L.xpt`, `DIQ_L.xpt` and `SMQ_L.xpt`. Existing files are not
replaced. File hashes are recorded in `outputs/tables/ml_data_audit.json`.
Only the recent cycle is used for modelling. SQL joins and recoding are in
`sql/ml_features.sql`; the original assay pipeline supplies the two labels.

The command replaces these aggregate outputs under `outputs/tables/`:

- `ml_data_audit.json`: cohort counts, predictor missingness and source hashes.
- `ml_performance.csv`: weighted and unweighted validation metrics.
- `ml_assay_comparison.csv`: converted-minus-raw changes using identical predictions.
- `ml_calibration.csv`: counts and weighted risks within fixed probability bins.
- `ml_folds.csv`: fold sizes, case counts and PSU-overlap checks.
- `ml_run_status.json`: settings, predictor list and software versions.

It also replaces `report/ml_initial_results.md`. It does not overwrite the
original survey estimates or figures. Participant-level predictions and trained
models are not saved. The [analysis plan](ml_analysis_plan.md) explains model
settings, fold construction, weighting and the limits of this first comparison.

The full test suite contains 32 tests when the optional ML packages are present.
Eight model and validation tests are skipped if scikit-learn is absent; the original analysis
does not require that package. The model run stops on missing outcome classes,
overlapping PSU groups, incomplete predictions or logistic convergence warnings.

The `-Validation` command requires the initial `ml_performance.csv` and checks
that seed-42 results agree with it. It adds five-seed split ranges, conditional
survey-group intervals and a calibration report. See
[validation methods](ml_validation_methods.md) for assumptions and output names.
The intervals condition on fixed predictions and are not full performance
confidence intervals. The R figure command is:

```powershell
Rscript scripts/visualisation/create_ml_calibration.R .
```

It produces Figure 3 in PNG and PDF format using base R; no extra R packages are
needed. When Rscript is not on PATH, use the full path to the installed executable.
