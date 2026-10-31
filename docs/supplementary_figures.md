# Supplementary figure documentation

`scripts/visualisation/create_supplementary_figures.R` generates aggregate-data figures for cohort flow and missing-data scenarios. Inputs are the saved JSON and CSV files in `outputs/tables/`. The script uses base R graphics and `jsonlite`; no participant-level data are read or changed.

## Execution

```text
Rscript scripts/visualisation/create_supplementary_figures.R .
```

An optional second argument specifies the output folder. The default is `outputs/figures/`. Figures are exported as PNG and PDF, with an R session record.

## Interpretation

Cohort counts are unweighted. Paired differences are expressed in percentage points. The missing-data scenario line combines observed weighted outcomes with assumed missing-group outcomes; its endpoints are identification bounds rather than confidence limits or predictions.

The script plots existing results without refitting the analysis. Sampling intervals condition on fixed conversion coefficients and do not include missing-data bias.
