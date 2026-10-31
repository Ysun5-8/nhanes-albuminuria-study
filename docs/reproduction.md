# Reproducing the NHANES albuminuria analysis

Run commands from the repository root unless stated otherwise. The instructions
below target 64-bit Windows, matching the recorded analysis environment. No command
requires the original author's drive letters or folder names.

## 1. Recorded software

The existing project interpreter reports **Python 3.12.10**, 64-bit AMD64.
The R session records and the current runtime report **R 4.6.1
(2026-06-24 ucrt)**, x86_64 Windows. The recorded operating system is Windows 11
build 26300. These are observed versions, not minimum-version claims.

Python analysis code directly imports NumPy **2.5.4**, pandas **2.3.3** and SciPy
**1.18.1**. SQL preparation uses Python's standard-library `sqlite3` (SQLite 3.49.1 in the validated runtime); no additional database package is needed. Tests use standard-library `unittest`. The full
existing package snapshot is [environment-lock.txt](environment-lock.txt); it
also includes notebook and development packages beyond the analysis requirements.

The R package list comes from explicit namespace calls in the scripts, the two
saved session records and the installed DESCRIPTION dependency metadata.

| R package | Observed version | Role/evidence |
|---|---|---|
| `foreign` | 0.8-91 | Direct XPT import; bundled/recommended package |
| `survey` | 4.5 | Direct survey estimation and validation |
| `jsonlite` | 2.0.0 | Direct JSON input/output |
| `Matrix` | 1.7-5 | `survey` dependency; session record |
| `survival` | 3.8-6 | `survey` dependency; session record |
| `lattice` | 0.22-9 | `survey` dependency; session record |
| `DBI` | 1.3.0 | Transitive dependency through `mitools`; session record |
| `mitools` | 2.7 | `survey` import; session record |
| `Rcpp` | 1.1.2 | `survey` import/linking dependency; session record |
| `minqa` | 1.2.8 | `survey` import; installed DESCRIPTION/version metadata |
| `numDeriv` | 2016.8-1.1 | `survey` import; installed DESCRIPTION/version metadata |
| `RcppArmadillo` | 15.6.2-1 | Declared linking dependency for building `survey`; installed metadata; not a direct script import |

`grid`, `methods`, `stats`, `graphics`, `grDevices`, `splines`, `utils` and `tools`
are supplied with R 4.6.1. The session also records `compiler` 4.6.1. Do not infer
that every installed package is a direct analysis dependency.

## 2. Set up a fresh computer

Install Python 3.12.10 and R 4.6.1 for 64-bit Windows. Install Git and clone this
repository. The existing XPT files and local environments are intentionally not
in Git. On the existing computer, reuse the current environment; do not recreate
or upgrade it merely to follow this fresh-computer example.

From a fresh checkout, create the Python environment and install the saved versions:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r docs\environment-lock.txt
.\.venv\Scripts\python.exe -B -c "import sys, numpy, pandas, scipy; print(sys.version); print(numpy.__version__, pandas.__version__, scipy.__version__)"
```

Confirm Python 3.12.10; the `py -3.12` selector alone does not guarantee that patch
version. No environment activation or PowerShell execution-policy change is needed.

For R, use the standard installation and make its `bin` folder available on PATH.
Alternatively, the launcher can discover a registered Windows R installation or
an optional repository-local `.tools/R/bin/Rscript.exe`. An explicit executable
override can be absolute or relative to the repository.

The following R commands install the observed external package versions into the
ignored project-local `.r-library` folder. Run them in an R 4.6.1 session whose
working directory is the repository root. This setup step requires internet access;
the analysis itself can use cached data without a network connection.

```r
stopifnot(as.character(getRversion()) == "4.6.1")
lib <- file.path(getwd(), ".r-library")
dir.create(lib, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))

versions <- c(DBI = "1.3.0", Rcpp = "1.1.2", RcppArmadillo = "15.6.2-1",
              minqa = "1.2.8", numDeriv = "2016.8-1.1", mitools = "2.7",
              jsonlite = "2.0.0", survey = "4.5")
for (package in names(versions)) {
  url <- paste0("https://cloud.r-project.org/bin/windows/contrib/4.6/",
                package, "_", versions[[package]], ".zip")
  install.packages(url, repos = NULL, type = "win.binary", lib = lib)
}
expected <- c(versions, foreign = "0.8-91", Matrix = "1.7-5",
              survival = "3.8-6", lattice = "0.22-9")
observed <- vapply(names(expected), function(package) {
  packageDescription(package, fields = "Version")
}, character(1))
stopifnot(all(observed == expected))
print(observed)
```

`foreign`, `Matrix`, `survival` and `lattice` were supplied in the R installation
used here; the check above confirms their versions. Exact external binary URLs
returned HTTP 200 during the original availability check, but CRAN may later replace older
binaries. If an exact version is unavailable or a check fails, stop and resolve the
package version from an official CRAN archive; do not silently install a newer
version and describe it as the validated environment. This is a pinned recipe,
not a vendored package archive or a guarantee of future binary availability.

## 3. Obtain the four official raw files

Create `data/raw/` beneath the repository and place the files directly inside it.
Keep their `.xpt` extension; do not save a codebook HTML page as an XPT file.

| Cycle and file | Official download | Codebook |
|---|---|---|
| 2017–March 2020 demographics: `P_DEMO.xpt` | [P_DEMO.XPT](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DEMO.XPT) | [P_DEMO documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DEMO.htm) |
| 2017–March 2020 urine laboratory: `P_ALB_CR.xpt` | [P_ALB_CR.XPT](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_ALB_CR.XPT) | [P_ALB_CR documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_ALB_CR.htm) |
| August 2021–August 2023 demographics: `DEMO_L.xpt` | [DEMO_L.XPT](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DEMO_L.XPT) | [DEMO_L documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DEMO_L.htm) |
| August 2021–August 2023 urine laboratory: `ALB_CR_L.xpt` | [ALB_CR_L.XPT](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/ALB_CR_L.XPT) | [ALB_CR_L documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/ALB_CR_L.htm) |

For a fresh checkout with no raw files, these are the equivalent PowerShell commands:

```powershell
New-Item -ItemType Directory -Force data\raw | Out-Null
$files = @(
    @{ Year = '2017'; Stem = 'P_DEMO' },
    @{ Year = '2017'; Stem = 'P_ALB_CR' },
    @{ Year = '2021'; Stem = 'DEMO_L' },
    @{ Year = '2021'; Stem = 'ALB_CR_L' }
)
foreach ($file in $files) {
    $destination = Join-Path 'data\raw' ($file.Stem + '.xpt')
    if (-not (Test-Path -LiteralPath $destination)) {
        $url = 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/' +
               $file.Year + '/DataFiles/' + $file.Stem + '.XPT'
        Invoke-WebRequest -Uri $url -OutFile $destination
    }
}
Get-FileHash data\raw\*.xpt -Algorithm SHA256
```

This example skips existing files. Compare hashes with the preserved values in
[input integrity record](input_integrity.md). A mismatch
requires checking whether CDC revised a file; do not overwrite the original cache.

## 4. Reproduce in order

The first test command uses synthetic examples and does not replace analysis outputs.
The subsequent analysis commands **do replace** the named files listed below.
Run them in a disposable checkout or review copy if existing validated evidence
must be preserved.

```powershell
# Python tests, SQL preparation audit, cohort audit, pilot and survey analysis.
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B -m scripts.sql_pipeline
.\.venv\Scripts\python.exe -B -m scripts.pilot.audit_cohort
.\.venv\Scripts\python.exe -B -m scripts.pilot.check_feasibility
.\.venv\Scripts\python.exe -B -m scripts.paired_analysis
.\.venv\Scripts\python.exe -B -m scripts.validation.check_sql_integration

# R helper tests, independent validation and robustness review in one command.
.\scripts\validation\run_validation.ps1 -ReviewRobustness
```

The launcher locates R in this order: explicit `-RscriptPath`, optional repository
`.tools/R/bin/Rscript.exe`, PATH, then the Windows R installer registry locations.
It uses explicit `-LibraryPath`, otherwise repository `.r-library` if present,
otherwise R's existing library settings. Relative overrides are repository-relative
even when the launcher is called from another folder. The caller's `R_LIBS_USER`
setting is restored on success or failure. The launcher never installs packages.

For example, an optional local installation can be selected explicitly:

```powershell
.\scripts\validation\run_validation.ps1 -RscriptPath '.tools\R\bin\Rscript.exe' -LibraryPath '.r-library' -ReviewRobustness
```

The same R steps can be run directly when `Rscript` is on PATH. These commands
explicitly select the project package library and use an absolute project root:

```powershell
$projectRoot = (Get-Location).Path
$previousLibrary = $env:R_LIBS_USER
try {
    $env:R_LIBS_USER = Join-Path $projectRoot '.r-library'
    Rscript --version
    Rscript --vanilla tests\test_reliability_helpers.R $projectRoot
    if ($LASTEXITCODE -ne 0) { throw 'R helper tests failed' }
    Rscript --vanilla scripts\validation\validate_with_r.R $projectRoot
    if ($LASTEXITCODE -ne 0) { throw 'R validation failed' }
    # This sources validation again, then writes robustness aggregates and reports.
    Rscript --vanilla scripts\validation\review_robustness.R $projectRoot
    if ($LASTEXITCODE -ne 0) { throw 'Robustness review failed' }
} finally {
    $env:R_LIBS_USER = $previousLibrary
}
```

For validation alone, use `run_validation.ps1` without `-ReviewRobustness`.
The launcher stops on a nonzero R exit status. When running R commands individually,
check each exit status and stop on failure rather than continuing the sequence.

## 5. Files replaced by analysis entry points

All paths below are relative to the repository; the directory layout is unchanged.

| Entry point | Named files replaced |
|---|---|
| `scripts.sql_pipeline` | `outputs/tables/sql_cohort_flow.json` |
| `scripts.validation.check_sql_integration` | `outputs/tables/sql_integration_checks.json`; with `--baseline`, writes `sql_migration_validation.json` instead |
| `scripts.pilot.audit_cohort` | `outputs/tables/mec_missingness_audit.json` |
| `scripts.pilot.check_feasibility` | `outputs/tables/feasibility_summary.json` |
| `scripts.paired_analysis` | `outputs/tables/paired_survey_analysis.json` |
| `validate_with_r.R` | `outputs/tables/r_survey_results.csv`, `r_python_comparison.csv`, `r_unweighted_qc_comparison.csv`, `r_validation_status.json`; `report/r_survey_validation.md`, `report/r_validation_session.txt` |
| `review_robustness.R` | Everything written by validation, plus `outputs/tables/reporting_reliability.csv`, `missingness_demographic_review.csv`, `paired_missingness_stress_test.csv`, `response_cell_weighting_diagnostics.csv`, `response_weighting_sensitivity.csv`, `robustness_review_summary.json`; `report/robustness_reliability_review.md`, `report/robustness_review_session.txt` |

The shorthand filenames in the last two rows remain under `outputs/tables/`.
No listed entry point regenerates the historical `data_quality_summary.json` or
`report/initial_analysis.md`. Preserve both as historical records. Missing XPTs can
be downloaded by the Python loader; existing raw files are not replaced.

## 6. Expected checks and interpretation

The current suite has 32 Python tests when the optional ML packages are loaded
through `scripts/ml/run_ml.ps1 -Test`; otherwise eight ML tests are skipped.
The survey workflow also has 13 SQL flow reconciliation checks, 11 R helper
assertions, 216 survey comparisons and seven unweighted QC checks. The
[ML reproduction guide](ml_reproduction.md) covers the model and calibration runs. Design: 15 strata, 30 PSUs and 15 degrees of freedom.
Recent-cycle cohort: 7,809 demographic adults, 6,064 examined and 5,910 complete urine
records; 154 examined adults lack results. These are reference findings, not values
hard-coded into the analysis.

Primary paired change is approximately **1.0633 percentage points**, with t Wald
95% CI **0.6770 to 1.4496 percentage points**. Inspect all aggregate files and fail
flags, not just this rounded summary. Sampling intervals do not include assay-bridge
uncertainty or resolve missing-data assumptions. See the protocol for the estimand.

The reproduction changes were tested in a separate review copy using the existing
installed runtimes and raw cache. A fresh package installation was not performed
over the current environments. Exact binary availability and recorded versions were
checked separately. All original validated outputs and raw hashes were preserved.

SQL migration reproduced 373 baseline numeric values within absolute/relative tolerance 1e-12. See the [SQL query map and migration evidence](sql_data_pipeline.md).
