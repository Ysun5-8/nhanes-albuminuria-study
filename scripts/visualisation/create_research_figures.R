# Research figures from original XPT files and validated aggregate estimates.
# Rscript scripts/visualisation/create_research_figures.R <project-root> [output-folder]
args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args)) normalizePath(args[1], mustWork = TRUE) else getwd()
out <- if (length(args) >= 2) args[2] else file.path(root, "outputs", "figures")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
stopifnot(requireNamespace("foreign", quietly = TRUE), requireNamespace("jsonlite", quietly = TRUE))
tab <- function(name) read.csv(file.path(root, "outputs", "tables", name), stringsAsFactors = FALSE)
results <- tab("r_survey_results.csv")
primary <- subset(results, scenario == "primary")
reliability <- tab("reporting_reliability.csv")

# Read locally cached files only; never download or overwrite source data.
demo <- foreign::read.xport(file.path(root, "data", "raw", "DEMO_L.xpt"))
lab <- foreign::read.xport(file.path(root, "data", "raw", "ALB_CR_L.xpt"))
stopifnot(!anyDuplicated(demo$SEQN), !anyDuplicated(lab$SEQN), all(lab$SEQN %in% demo$SEQN))
frame <- merge(demo, lab, by = "SEQN", all.x = TRUE)
eligible <- with(frame, is.finite(RIDAGEYR) & RIDAGEYR >= 20 &
                   is.finite(WTMEC2YR) & WTMEC2YR > 0 &
                   is.finite(URXUMA) & URXUMA >= 0 & is.finite(URXUCR) & URXUCR > 0)
frame <- frame[eligible, ]
raw <- with(frame, 100 * URXUMA / URXUCR)
harm <- with(frame, 100 * pmax(0, -1.643 + 1.189 * URXUMA) / URXUCR)
group <- ifelse(raw < 30 & harm >= 30, "Upward",
                ifelse(raw >= 30 & harm < 30, "Downward", "Unchanged"))
count <- function(key) reliability$events[match(key, reliability$outcome)]
stopifnot(length(raw) == unique(primary$n_domain), sum(group == "Upward") == count("upward"),
          sum(group == "Downward") == count("downward"),
          sum(raw >= 30) == count("raw"), sum(harm >= 30) == count("harmonised"))

save_plot <- function(name, width, height, draw) {
  for (ext in c("png", "pdf")) {
    path <- file.path(out, paste0(name, ".", ext))
    if (ext == "png") png(path, width = width, height = height, units = "in", res = 300)
    else pdf(path, width = width, height = height, useDingbats = FALSE)
    tryCatch({par(family = "sans", cex = 0.85, mgp = c(2.5, 0.7, 0), tcl = -0.25); draw()},
             finally = dev.off())
  }
}
colours <- c(Unchanged = "#B6B6B6", Upward = "#0072B2", Downward = "#D55E00")
symbols <- c(Unchanged = 16, Upward = 17, Downward = 15)
save_plot("figure_1_uacr_reclassification", 9, 5.5, function() {
  layout(matrix(c(1, 2, 3, 3), nrow = 2, byrow = TRUE), heights = c(1, 0.13))
  par(mar = c(4.5, 6.5, 2.8, 1.5), oma = c(0.5, 0.5, 0.5, 0.5), mgp = c(4.3, 0.8, 0))
  for (zoom in c(FALSE, TRUE)) {
    # log10(1+x) retains zero-valued harmonised UACR without adding fake data.
    transform <- if (zoom) identity else function(x) log10(1 + x)
    limit <- if (zoom) 60 else max(c(raw, harm)) * 1.05
    ticks <- if (zoom) seq(0, 60, 15) else c(0, 1, 10, 30, 100, 1000, 10000, 100000)
    ticks <- ticks[ticks <= limit]
    plot(NA, xlim = transform(c(0, limit)), ylim = transform(c(0, limit)),
         xaxs = "i", yaxs = "i", axes = FALSE, asp = 1,
         xlab = "", ylab = "Harmonised UACR (mg/g)")
    axis(1, at = transform(ticks), labels = ticks)
    mtext("Raw UACR (mg/g)", side = 1, line = 2.5)
    axis(2, at = transform(ticks), labels = ticks, las = 1)
    box(bty = "l")
    abline(a = 0, b = 1, col = "grey70", lwd = 0.7)
    abline(v = transform(30), h = transform(30), lty = 2, col = "grey40", lwd = 0.8)
    for (category in names(colours)) {
      keep <- group == category & raw <= limit & harm <= limit
      points(transform(raw[keep]), transform(harm[keep]), col = colours[category],
             pch = symbols[category], cex = if (category == "Unchanged") 0.35 else 0.9)
    }
    mtext(if (zoom) "B  Threshold region" else "A  Full range", side = 3, adj = 0, line = 0.8, font = 2)
  }
  par(mar = c(0, 0, 0, 0))
  plot.new()
  legend("center", legend = c("Unchanged", "Upward", "Downward"),
         col = colours, pch = symbols, horiz = TRUE, bty = "n", cex = 0.85)
})

# Retain prevalence and the paired difference in a table instead of a second figure.
keys <- c("raw_at_or_above_30", "harmonised_at_or_above_30", "paired_difference_harmonised_minus_raw", "any_reclassification")
d <- primary[match(keys, primary$outcome), ]
table1 <- data.frame(Outcome = c("Raw UACR >=30 mg/g", "Harmonised UACR >=30 mg/g", "Paired difference", "Any reclassification"),
                     Unit = c("%", "%", "percentage points", "%"), N = d$n_domain,
                     Estimate = sprintf("%.2f", 100 * d$estimate),
                     CI95 = sprintf("%.2f to %.2f", 100 * d$ci95_lower, 100 * d$ci95_upper))
write.csv(table1, file.path(out, "table_1_primary_results.csv"), row.names = FALSE)

scenarios <- c("primary", "exclude_below_detection_either_analyte", "exclude_negative_bridge_values",
               "strictly_greater_than_30", "published_rounded_raw_URDACT", "unclipped_bridge")
d <- subset(results, outcome == "paired_difference_harmonised_minus_raw")
d <- d[match(scenarios, d$scenario), ]
stopifnot(!anyNA(d$scenario), all(d$ci95_lower <= d$estimate), all(d$ci95_upper >= d$estimate))
labels <- c("Primary", "Exclude below detection*", "Exclude negative predictions*",
            "Threshold >30 mg/g", "Published rounded raw UACR", "No zero-clipping")
save_plot("figure_2_sensitivity", 10, 4.2, function() {
  par(mar = c(4.5, 0.5, 1, 0.5))
  plot.new(); plot.window(xlim = c(-1.9, 3.4), ylim = c(0.4, 7.5), xaxs = "i")
  y <- 6:1
  text(-1.85, 7.1, "Analysis", adj = 0, font = 2)
  text(2.0, 7.1, "n", font = 2)
  text(2.7, 7.1, "Difference (95% CI)", font = 2)
  segments(-1.85, 6.7, 3.3, 6.7, col = "grey65")
  segments(0, 0.65, 0, 6.4, lty = 2, col = "grey60")
  text(-1.85, y, labels, adj = 0, cex = 0.85)
  segments(100 * d$ci95_lower, y, 100 * d$ci95_upper, y, lwd = 1.2)
  points(100 * d$estimate, y, pch = 19, cex = 0.85)
  text(2.0, y, format(d$n_domain, big.mark = ","), cex = 0.85)
  text(2.7, y, sprintf("%.2f (%.2f to %.2f)", 100 * d$estimate,
                       100 * d$ci95_lower, 100 * d$ci95_upper), cex = 0.85)
  axis(1, at = seq(0, 1.5, 0.5), pos = 0.5)
  mtext("Paired difference (percentage points)", side = 1, line = 2.5, at = 0.85)
})

in_zoom <- raw <= 60 & harm <= 60
legend_text <- c(
  "# Figure and table legends", "",
  "**Figure 1. Raw and harmonised urine albumin-to-creatinine ratio (UACR) in NHANES August 2021-August 2023.** Each point represents one complete-data adult aged 20 years or older with a positive examination weight. Panel A includes all participants on log10(1 + UACR) axes, labelled in original mg/g units; the transformation retains harmonised zero values. Panel B shows a display window of 0-60 mg/g on both axes, on linear scales. Dashed lines mark the inclusive 30 mg/g threshold; the solid diagonal marks equality. Blue triangles indicate upward crossings and orange squares downward crossings. Grey circles indicate unchanged classification. Points are unweighted and may overlap; point density does not represent population prevalence. The conversion was applied to albumin only, with negative predictions clipped to zero.",
  sprintf("Panel A contains %s participants, including %s upward and %s downward crossings. Panel B displays %s participants, including %s upward and %s downward crossings; %s participants fall outside its window. The window was selected for visual inspection after analysis, not for cohort selection.",
          length(raw), sum(group == "Upward"), sum(group == "Downward"), sum(in_zoom),
          sum(in_zoom & group == "Upward"), sum(in_zoom & group == "Downward"), sum(!in_zoom)), "",
  "**Figure 2. Sensitivity of the paired difference in UACR threshold prevalence to analytical choices.** Points show harmonised-minus-raw differences; horizontal lines show survey-adjusted t Wald 95% confidence intervals with 15 design degrees of freedom. The dashed line marks zero difference. Sample sizes and numerical estimates are provided alongside the plot. Asterisks identify exclusions that change the analysis domain. Intervals condition on fixed conversion coefficients and do not include potential missing-data bias.", "",
  "**Table 1. Primary survey-weighted results.** Estimates use the complete-data adult domain, examination weights, survey strata and primary sampling units. Confidence intervals use Taylor linearisation and the t distribution with 15 design degrees of freedom. Differences are calculated within participants. Values are rounded independently. A single UACR measurement does not establish a CKD diagnosis."
)
writeLines(legend_text, file.path(out, "research_figure_legends.md"))
writeLines(capture.output(sessionInfo()), file.path(out, "research_visualisation_session.txt"))
message(sprintf("Validated %s adults, %s upward and %s downward crossings. Zoom: %s adults.",
                length(raw), sum(group == "Upward"), sum(group == "Downward"), sum(in_zoom)))
