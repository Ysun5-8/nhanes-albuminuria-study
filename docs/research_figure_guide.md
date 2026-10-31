# Figure documentation

`scripts/visualisation/create_research_figures.R` generates Figures 1–2 and the primary results table from the project data and validated aggregate estimates.

## Execution

From the repository root:

```text
Rscript scripts/visualisation/create_research_figures.R .
```

Dependencies are R's `foreign` package and `jsonlite`. Inputs are the cached DEMO_L and ALB_CR_L XPT files and the aggregate tables in `outputs/tables/`. Outputs are 300 dpi PNG figures, vector PDFs, the primary results CSV, figure legends and an R session record in `outputs/figures/`. Source data are unchanged.

## Outputs

- **Figure 1:** raw versus harmonised UACR, with a full-range log10(1+x) panel and a linear 0–60 mg/g panel. Symbols identify upward, downward and unchanged classification. The restricted panel includes all threshold crossings.
- **Figure 2:** paired differences across sensitivity scenarios, with sample sizes and 95% confidence intervals.
- **Table 1:** survey-weighted prevalence, paired difference and any reclassification.

The [figure legends](../report/figure_legends.md) specify the transformation, display window and uncertainty methods. Scatterplot points are unweighted and may overlap. The conversion comparison does not independently validate the assay bridge. The plotting checks confirm agreement with saved participant counts; they do not assess all scientific assumptions.

## Model calibration figure

Figure 3 is generated separately after the ML validation run:

```text
Rscript scripts/visualisation/create_ml_calibration.R .
```

It uses base R and `outputs/tables/ml_calibration_intervals.csv`. The output is
`figure_3_ml_calibration.png` (300 dpi) and a vector PDF in `outputs/figures/`.
The two panels compare raw and converted outcomes against identical held-out
predictions, with participant counts beneath them. The
[Figure 3 legend](../report/ml_figure_legend.md) explains the conditional intervals
and sparse upper bands. Its uncertainty method differs from the survey intervals
in Figure 2.
