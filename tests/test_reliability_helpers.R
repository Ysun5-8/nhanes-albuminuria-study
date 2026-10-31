# Run: Rscript tests/test_reliability_helpers.R <project-root>
root <- commandArgs(trailingOnly = TRUE)[1]
source(file.path(root, "scripts/validation/reliability_helpers.R"))
# A small numerator alone is not a suppression criterion.
stopifnot(presentation_screen(.001, 1000, 1000, .0001, .003, 15, 1) == "present_screen_pass")
# Exercise the actual policy boundaries, including the .30 width cutoff and low-df review branch.
stopifnot(presentation_screen(.01, 29, 100, .005, .02, 15, 1) == "suppress_size")
stopifnot(presentation_screen(.01, 100, 29, .005, .02, 15, 1) == "suppress_size")
stopifnot(presentation_screen(.01, 100, 100, 0, .06, 15, 1) == "suppress_width")
stopifnot(presentation_screen(.5, 100, 100, 0, .30, 15, 50) == "suppress_width")
stopifnot(presentation_screen(.5, 100, 100, .49, .51, 7, 50) == "review")
stopifnot(presentation_screen(0, 100, 100, 0, .04, 15, 0) == "review")
# With simple-random-sample variance, KG reduces to the exact binomial CI.
p <- .1
n <- 100
kg <- kg_interval(p, p * (1 - p) / n, n)
stopifnot(max(abs(c(kg$lower, kg$upper) - binom.test(10, 100)$conf.int)) < 1e-12)
# Effective sample size must be capped, even if stratification reduces variance.
stopifnot(kg_interval(.1, .00001, 100)$used == 100)
stopifnot(all.equal(unname(paired_missing_bounds(.1, .2)), c( - .12, .28)))
stopifnot(all.equal(unname(paired_missing_bounds(.1, 0)), c(.1, .1)))
cat("All 11 R reliability-helper assertions passed.\n")
