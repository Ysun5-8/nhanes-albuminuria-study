# Run from a terminal:
# Rscript scripts/visualisation/create_supplementary_figures.R <project-root> [output-folder]
# Uses aggregate outputs only. It does not refit models or read participant data.
args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args)) normalizePath(args[1], mustWork = TRUE) else getwd()
out <- if (length(args) >= 2) args[2] else file.path(root, "outputs", "figures")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("Install jsonlite first: install.packages('jsonlite')")
}
tables <- file.path(root, "outputs", "tables")
read_table <- function(name) read.csv(file.path(tables, name), stringsAsFactors = FALSE)
blue <- "#176B87"
orange <- "#B55A30"

# Export both a presentation PNG and a scalable PDF from the same drawing code.
save_figure <- function(name, draw) {
  for (format in c("png", "pdf")) {
    path <- file.path(out, paste0(name, ".", format))
    if (format == "png") png(path, width = 2400, height = 1500, res = 240)
    else pdf(path, width = 10, height = 6.25, useDingbats = FALSE)
    tryCatch({par(family = "sans", col = "#243746", col.axis = "#243746"); draw()},
             finally = dev.off())
  }
}

audit <- jsonlite::fromJSON(file.path(tables, "mec_missingness_audit.json"))
cohort <- audit$cycles[["2021-2023"]]
stopifnot(!is.null(cohort),
          cohort$n_adults_demographics == cohort$n_adults_positive_mec_weight +
            cohort$n_adults_interview_only,
          cohort$n_adults_positive_mec_weight == cohort$n_eligible_valid_lab +
            cohort$n_eligible_missing_or_invalid_lab)
save_figure("01_cohort_flow", function() {
  par(mar = c(2, 1, 4, 1))
  plot.new(); plot.window(xlim = c(0, 10), ylim = c(0, 10))
  title("Who was included?", sub = "NHANES August 2021-August 2023 | Unweighted adult counts")
  box_label <- function(x, y, label, fill = "#EAF3F6") {
    rect(x - 1.9, y - 0.65, x + 1.9, y + 0.65, col = fill, border = blue)
    text(x, y, label, cex = 0.95)
  }
  arrows(3, 7.85, 3, 6.15, length = 0.1)
  arrows(3, 4.85, 3, 3.15, length = 0.1)
  arrows(4.9, 8.5, 6.1, 8.5, length = 0.1)
  arrows(4.9, 5.5, 6.1, 5.5, length = 0.1)
  box_label(3, 8.5, sprintf("Adults aged 20+\nn = %s", format(cohort$n_adults_demographics, big.mark = ",")))
  box_label(3, 5.5, sprintf("Positive examination weight\nn = %s", format(cohort$n_adults_positive_mec_weight, big.mark = ",")))
  box_label(3, 2.5, sprintf("Complete urine data\nn = %s", format(cohort$n_eligible_valid_lab, big.mark = ",")))
  box_label(8, 8.5, sprintf("Interview only\nn = %s", format(cohort$n_adults_interview_only, big.mark = ",")), "#FAEEE8")
  box_label(8, 5.5, sprintf("Missing urine results\nn = %s", cohort$n_eligible_missing_or_invalid_lab), "#FAEEE8")
})

stress <- read_table("paired_missingness_stress_test.csv")
save_figure("04_missing_data_assumptions", function() {
  par(mar = c(8, 6, 4, 2))
  x <- 100 * stress$missing_group_mean_paired_change
  y <- 100 * stress$all_examined_adult_paired_change
  plot(x, y, type = "o", pch = 19, col = blue, lwd = 2, bty = "n",
       main = "What if the missing adults had different results?",
       xlab = "Assumed mean paired change in the missing group (percentage points)",
       ylab = "Paired change among all examined adults (percentage points)")
  abline(h = 0, v = 0, lty = 2, col = "#778899")
  mtext("A scenario analysis, not a confidence interval. Extreme assumptions are not predictions.\nThe line includes sampling-weighted observed outcomes and assumed missing outcomes.",
        side = 1, line = 6, cex = 0.75)
})
writeLines(capture.output(sessionInfo()), file.path(out, "visualisation_session.txt"))
message("Figures saved to: ", normalizePath(out))
