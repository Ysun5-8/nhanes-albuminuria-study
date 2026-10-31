# SQL data preparation

The Python analysis uses SQLite for participant joins, eligibility flags, assay
calculations and descriptive summaries. SQLite is supplied by Python's standard
library; no database server or additional package is required. The validated
runtime uses SQLite 3.49.1.

## Data flow

1. `fetch_or_load()` reads the original NHANES XPT files with pandas and restores
   the exact XPORT zero sentinel. It does not otherwise round concentrations.
2. `scripts/sql_pipeline.py` loads separate `demographics` and `urine` tables into
   a temporary in-memory database. SQL checks reject missing/nonfinite participant
   identifiers, duplicate identifiers and urine records without demographics.
   Unique indexes enforce one record per SEQN in each input table.
3. `sql/prepare_participants.sql` left-joins urine onto demographics. Its views
   define examination eligibility, valid urine, the complete-adult domain, raw
   UACR, converted albumin and threshold classifications. Demographic records
   without urine results remain present. The historical cycle is not converted.
4. Python receives the prepared records. The paired analysis retains every
   positive-weight MEC participant before selecting the complete-adult domain
   inside its survey estimator. It does not drop children or missing-urine adults
   from the survey design.
5. SQL aggregate queries produce cohort counts, reclassification counts and
   demographic missingness summaries. Only aggregates are written to disk.

SQL uses the loader's registered `is_finite()` function to distinguish finite
numbers from NULL and infinity. Missing or invalid urine yields NULL UACR and
classification, not a negative outcome. Zero-clipping applies only to negative
converted albumin from valid urine. Python's false placeholders outside the
analysis domain do not enter the outcome numerator or denominator.

## Query and caller map

| File | Responsibility | Called by |
|---|---|---|
| `sql/prepare_participants.sql` | Demographics-first join, eligibility, ratios and classifications | `scripts/sql_pipeline.py` through both audit and feasibility entry points |
| `sql/cohort_flow.sql` | Counts before and after examination and urine eligibility | `scripts.sql_pipeline`; also attached to prepared frames |
| `sql/reclassification.sql` | Paired unweighted threshold crossings | `scripts.pilot.check_feasibility` |
| `sql/missingness_by_demographics.sql` | Age, sex and race/ethnicity grouped missingness | `scripts.pilot.audit_cohort` |
| `scripts/paired_analysis.py` | Consumes SQL variables; calculates weighted estimates and Taylor-linearised confidence intervals | Primary analysis entry point |
| `scripts/validation/check_sql_integration.py` | Reconciles SQL counts with analysis outputs; optional migration comparison | Validation entry point |

The cohort audit retains Python checks of the examination denominator and detailed
missing-analyte categories. This provides a separate check of SQL eligibility.
The grouped SQL weighted percentages are descriptive; they do not calculate
survey standard errors. R continues to import the original XPT files and derive
its own variables, preserving an independent check of the SQL/Python pipeline.
Figure scripts continue to use the validated analysis outputs and R calculations.

## Execution

Run from the repository root, using the existing Python environment:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.sql_pipeline
.\.venv\Scripts\python.exe -B -m scripts.pilot.audit_cohort
.\.venv\Scripts\python.exe -B -m scripts.pilot.check_feasibility
.\.venv\Scripts\python.exe -B -m scripts.paired_analysis
.\.venv\Scripts\python.exe -B -m scripts.validation.check_sql_integration
```

These commands replace their named aggregate outputs. No participant-level
database is persisted. SQL templates use validated cycle names, allow-listed
weight/group columns and quoted source identifiers; they are executed through
the Python loader, which supplies the tables and `is_finite()` function.

The full test and independent R commands are in [reproduction.md](reproduction.md).

## Migration verification

The original Python entry points were rerun in a review copy before modification.
After integration, the three aggregate JSON outputs agreed with that baseline
for 373 numeric values and all nine text values, using absolute and relative
tolerances of 1e-12. This includes both cycles' cohort audits, feasibility counts,
the primary estimates, all five sensitivity analyses and missing-outcome bounds.
The baseline file hashes and comparison counts are retained in
`outputs/tables/sql_migration_validation.json`.

The standard SQL reconciliation adds 13 cross-output count checks. At the SQL integration stage, nineteen
Python tests passed, including seven SQL-specific tests of NULL identifiers,
invalid measurements, nonfinite weights, absent specimens, historical-cycle
handling, ambiguous columns and empty aggregates. Independent R validation
passes all 216 numeric comparisons and seven count checks; the robustness run
also passes all 11 R helper assertions. The current full suite contains 32 Python
tests with the optional ML packages; see [reproduction.md](reproduction.md).

To compare against a separately retained baseline directory:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.validation.check_sql_integration --baseline PATH_TO_BASELINE_TABLES
```

The optional comparison writes `sql_migration_validation.json`. A normal run
writes `sql_integration_checks.json`, preserving the migration evidence. Shared
pipeline consistency is not independent statistical validation; the separate R
implementation supplies that additional check. Neither check validates the
assay bridge or missing-data assumptions.
