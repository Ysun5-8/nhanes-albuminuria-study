# Small, testable helpers for the reporting screen. Inputs use proportions,
# not percentages: 0.05 means a confidence interval five percentage points wide.

# Return the interval and both effective denominators: one for the
# sample-size screen and one for the finite-df interval calculation.
kg_interval <- function(p, variance, n, df = n - 1) {
  stopifnot(is.finite(p), p >= 0, p <= 1, is.finite(variance), variance >= 0, n > 0)
  # Korn-Graubard's beta construction substitutes an effective denominator
  # p*(1-p)/Var(p) for the binomial sample size. Cap it at actual n as directed
  # by NCHS. For a boundary estimate use n; a review flag is added separately.
  neff <- if (p == 0 || p == 1) n else p * (1 - p) / variance
  # Match survey 4.5's finite-design-df adjustment. Its beta method uses the
  # design's df internally even though it ignores the supplied df argument.
  # Reducing n_eff widens the interval when there are few independent PSUs.
  adjusted_neff <- neff * (qt(.025, n - 1) / qt(.025, df)) ^ 2
  used <- min(n, adjusted_neff)
  successes <- p * used
  lower <- if (p == 0) 0 else qbeta(.025, successes, used - successes + 1)
  upper <- if (p == 1) 1 else qbeta(.975, successes + 1, used - successes)
  list(lower = lower, upper = upper, neff = neff, size_neff = min(n, neff), used = used)
}

presentation_screen <- function(p, n, neff, lower, upper, df, events) {
  # Apply the size, interval-width and df branches in the NCHS flowchart.
  # A relative width >130% matters only if absolute width exceeds .05.
  # There is no rule that automatically suppresses a nonzero numerator <30.
  width <- upper - lower
  relative <- if (p > 0) width / p else Inf
  if (n < 30 || neff < 30) return("suppress_size")
  if (width >= .30 || (width > .05 && relative > 1.30)) return("suppress_width")
  if (events == 0 || events == n || df < 8 || width <= 0) return("review")
  "present_screen_pass"
}

paired_missing_bounds <- function(observed_difference, missing_share) {
  stopifnot(is.finite(observed_difference), abs(observed_difference) <= 1,
            is.finite(missing_share), missing_share >= 0, missing_share <= 1)
  # The missing group's mean paired change q lies in [-1,1]. The combined
  # estimate is (1-m)*observed + m*q. These are bounds, not confidence limits.
  contribution <- (1 - missing_share) * observed_difference
  c(lower = contribution - missing_share, upper = contribution + missing_share)
}
