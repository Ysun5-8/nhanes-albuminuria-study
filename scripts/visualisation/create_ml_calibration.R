# Calibration and bin counts from the ML validation aggregates.
# Rscript scripts/visualisation/create_ml_calibration.R <project-root>
args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args)) normalizePath(args[1], mustWork = TRUE) else getwd()
dat <- read.csv(file.path(root, "outputs/tables/ml_calibration_intervals.csv"))
out <- file.path(root, "outputs/figures")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
models <- c("logistic", "gradient_boosting")
titles <- c("Logistic regression", "Gradient boosting")
colours <- c("#0072B2", "#D55E00")
stopifnot(all(models %in% dat$model), all(dat$n > 0))

draw <- function() {
  layout(matrix(c(1, 2, 3, 4, 5, 5), nrow = 3, byrow = TRUE), heights = c(3.7, 1.6, 0.45))
  par(family = "sans", cex = 0.9, mgp = c(2.6, 0.65, 0), tcl = -0.25)
  for (k in seq_along(models)) {
    d <- dat[dat$model == models[k], ]
    d <- d[order(d$bin_lower), ]
    par(mar = c(4.1, 4.7, 2.5, 1))
    plot(NA, xlim = c(0, 100), ylim = c(0, 100), xaxs = "i", yaxs = "i",
         xlab = "Mean predicted probability (%)", ylab = "Observed proportion (%)",
         axes = FALSE, main = paste(LETTERS[k], titles[k]), cex.main = 1)
    axis(1, at = seq(0, 100, 20)); axis(2, at = seq(0, 100, 20), las = 1)
    abline(0, 1, col = "grey55", lty = 2)
    box(bty = "l")
    for (j in 1:2) {
      prefix <- c("raw", "converted")[j]
      low <- 100 * d[[paste0(prefix, "_lower")]]
      high <- 100 * d[[paste0(prefix, "_upper")]]
      x <- 100 * d$mean_prediction
      y <- 100 * d[[paste0(prefix, "_observed")]]
      good <- is.finite(low) & is.finite(high)
      segments(x[good], low[good], x[good], high[good],
               col = adjustcolor(colours[j], alpha.f = 0.5), lwd = 1)
      lines(x, y, col = colours[j], lty = j, lwd = 1.4)
      points(x, y, col = colours[j], pch = c(16, 17)[j], cex = 0.8)
    }
  }
  for (k in seq_along(models)) {
    d <- dat[dat$model == models[k], ]
    d <- d[order(d$bin_lower), ]
    par(mar = c(3.8, 4.7, 1.2, 1))
    labels <- c("0–5", "5–10", "10–20", "20–40", "40–60", "60–100")
    # Use ASCII labels in PDF devices with standard fonts.
    labels <- gsub("–", "-", labels)
    mid <- barplot(d$n, names.arg = labels, col = "grey78", border = NA,
                   ylim = c(0, max(dat$n) * 1.24), las = 1, cex.names = 0.8,
                   ylab = "Participants", xlab = "Predicted probability band (%)")
    text(mid, d$n, labels = d$n, pos = 3, cex = 0.75)
  }
  par(mar = c(0, 0, 0, 0)); plot.new()
  legend("center", legend = c("Raw outcome", "Converted outcome", "Perfect calibration"),
         col = c(colours, "grey55"), lty = c(1, 2, 2), pch = c(16, 17, NA),
         horiz = TRUE, bty = "n", cex = 0.85, x.intersp = 1.4)
}
for (ext in c("png", "pdf")) {
  path <- file.path(out, paste0("figure_3_ml_calibration.", ext))
  if (ext == "png") png(path, width = 9, height = 7.5, units = "in", res = 300)
  else pdf(path, width = 9, height = 7.5, useDingbats = FALSE)
  tryCatch(draw(), finally = dev.off())
}
