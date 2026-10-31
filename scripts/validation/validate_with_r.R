# Independent validation of the Python analysis with R's survey package.
#
# Run from any working directory:
#   Rscript scripts/validation/validate_with_r.R C:/Project_x/nhanes-albuminuria-harmonisation
#
# This script reads the original XPT files, constructs outcomes in R, and asks
# survey::svymean to estimate variances. It does not import Python's prepared
# data or reuse its custom variance formula. Only aggregate outputs are saved.

# Running this script replaces its named aggregate outputs and reports.
# Use a separate review root when the existing evidence must be preserved.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("Supply exactly one argument: the project root.")
root <- normalizePath(args[1], winslash = "/", mustWork = TRUE)
for (pkg in c("foreign", "survey", "jsonlite")) {
  if (!requireNamespace(pkg, quietly = TRUE)) stop("Missing package: ", pkg)
}
library(survey)
# Fail rather than quietly choosing a correction if a stratum has only one PSU.
options(survey.lonely.psu = "fail")

# 1. Read demographics first so participants without urine results are retained.
# foreign::read.xport is a separate importer from pandas.read_sas.
demo_path <- file.path(root, "data/raw/DEMO_L.xpt")
lab_path <- file.path(root, "data/raw/ALB_CR_L.xpt")
demo <- foreign::read.xport(demo_path)
lab <- foreign::read.xport(lab_path)
stopifnot(!anyDuplicated(demo$SEQN), !anyDuplicated(lab$SEQN),
          all(lab$SEQN %in% demo$SEQN))
lab_columns <- c("URXUMA", "URXUCR", "URDACT", "URDUMALC", "URDUCRLC")
dat <- cbind(demo, lab[match(demo$SEQN, lab$SEQN), lab_columns])
dat <- dat[is.finite(dat$WTMEC2YR) & dat$WTMEC2YR > 0, ]
stopifnot(all(dat$RIDSTATR == 2),
          !anyNA(dat[c("SDMVSTRA", "SDMVPSU")]))
psus_per_stratum <- tapply(dat$SDMVPSU, dat$SDMVSTRA,
                          function(x) length(unique(x)))
stopifnot(all(psus_per_stratum >= 2))

# 2. Define the analytic subgroup (called a domain in survey statistics).
# A missing laboratory result is not a negative outcome. It is outside the
# complete-data domain but its participant remains in the full survey design.
dat$complete_adult <- is.finite(dat$RIDAGEYR) & dat$RIDAGEYR >= 20 &
  is.finite(dat$URXUMA) & dat$URXUMA >= 0 &
  is.finite(dat$URXUCR) & dat$URXUCR > 0
dat$raw_acr <- 100 * dat$URXUMA / dat$URXUCR
dat$bridge_unclipped <- - 1.643 + 1.189 * dat$URXUMA
dat$adjusted_acr <- 100 * pmax(dat$bridge_unclipped, 0) / dat$URXUCR

# 3. Specify the FULL MEC design before subsetting. PSU labels repeat across
# strata, so nest=TRUE makes the stratum/PSU combination the cluster identifier.
# No finite population correction is supplied, matching the Python analysis.
# Nest PSU identifiers within strata because their labels repeat.
make_design <- function(data) {
  svydesign(ids = ~ SDMVPSU, strata = ~ SDMVSTRA, weights = ~ WTMEC2YR,
            nest = TRUE, data = data)
}
full_design <- make_design(dat)
design_df <- degf(full_design)

# A small hand-calculated example checks domain subsetting when a PSU contains
# no domain participants. The mean is 1/2 and variance is 3/16, with df=2 in
# the full design. This guards against dropping empty-domain PSUs prematurely.
toy <- data.frame(SDMVSTRA = c(1, 1, 1), SDMVPSU = 1:3,
                  WTMEC2YR = c(1, 1, 1), domain = c(TRUE, TRUE, FALSE),
                  y = c(0, 1, NA))
toy_design <- make_design(toy)
toy_result <- svymean( ~ y, subset(toy_design, domain))
stopifnot(abs(coef(toy_result)[1] - 0.5) < 1e-12,
          abs(vcov(toy_result)[1, 1] - 3 / 16) < 1e-12)

# 4. Reconstruct each analysis, including all five sensitivity scenarios.
scenarios <- c("primary", "exclude_below_detection_either_analyte",
               "exclude_negative_bridge_values", "strictly_greater_than_30",
               "published_rounded_raw_URDACT", "unclipped_bridge")
rows <- list()
for (scenario in scenarios) {
  domain <- dat$complete_adult
  raw <- dat$raw_acr >= 30
  adjusted <- dat$adjusted_acr >= 30
  if (scenario == "exclude_below_detection_either_analyte") {
    domain <- domain & dat$URDUMALC == 0 & dat$URDUCRLC == 0
  } else if (scenario == "exclude_negative_bridge_values") {
    domain <- domain & dat$bridge_unclipped >= 0
  } else if (scenario == "strictly_greater_than_30") {
    raw <- dat$raw_acr > 30
    adjusted <- dat$adjusted_acr > 30
  } else if (scenario == "published_rounded_raw_URDACT") {
    domain <- domain & !is.na(dat$URDACT)
    raw <- dat$URDACT >= 30
  } else if (scenario == "unclipped_bridge") {
    adjusted <- (100 * dat$bridge_unclipped / dat$URXUCR) >= 30
  }
  # R propagates NA through comparisons; explicitly exclude unknown domain
  # membership. Do not replace missing outcome values with zero.
  domain[is.na(domain)] <- FALSE
  outcomes <- data.frame(
    raw_at_or_above_30 = as.numeric(raw),
    harmonised_at_or_above_30 = as.numeric(adjusted),
    paired_difference_harmonised_minus_raw = as.numeric(adjusted) - as.numeric(raw),
    any_reclassification = as.numeric(raw != adjusted),
    below_to_above = as.numeric(!raw & adjusted),
    above_to_below = as.numeric(raw & !adjusted))
  stopifnot(all(is.finite(as.matrix(outcomes[domain, ]))))
  current <- cbind(dat, outcomes)
  current$analysis_domain <- domain
  # subset() acts on the survey design, rather than deleting data before
  # constructing it. svymean estimates all six outcomes and their covariance.
  domain_design <- subset(make_design(current), analysis_domain)
  fit <- svymean(reformulate(names(outcomes)), domain_design)
  # confint defaults can differ between programs. Explicitly request the
  # protocol's t-based Wald interval using the FULL design degrees of freedom.
  interval <- confint(fit, level = 0.95, df = design_df)
  rows[[scenario]] <- data.frame(
    scenario = scenario, outcome = names(coef(fit)),
    estimate = unname(coef(fit)), standard_error = unname(SE(fit)),
    ci95_lower = interval[, 1], ci95_upper = interval[, 2],
    design_df = design_df, n_domain = sum(domain), row.names = NULL)
}
r_results <- do.call(rbind, rows)
rownames(r_results) <- NULL

# 5. Compare against the saved Python results, in proportion units (0 to 1).
# Absolute + relative tolerance accommodates harmless floating-point differences
# while being far smaller than the precision used in the displayed results.
baseline_path <- file.path(root, "outputs/tables/paired_survey_analysis.json")
baseline <- jsonlite::fromJSON(baseline_path, simplifyVector = FALSE)
abs_tol <- 1e-10
rel_tol <- 1e-8
comparison <- list()
fields <- c("estimate", "standard_error", "ci95_lower", "ci95_upper",
            "design_df", "n_domain")
for (i in seq_len(nrow(r_results))) {
  row <- r_results[i, ]
  expected <- if (row$scenario == "primary") baseline$primary[[row$outcome]] else
    baseline$sensitivity[[row$scenario]][[row$outcome]]
  if (is.null(expected)) stop("Missing Python comparison outcome: ", row$outcome)
  for (field in fields) {
    py <- expected[[field]]
    rv <- row[[field]]
    if (is.null(py) || !is.finite(py) || !is.finite(rv)) stop("Invalid comparison value")
    exact <- field %in% c("design_df", "n_domain")
    tolerance <- if (exact) 0 else abs_tol + rel_tol * abs(py)
    comparison[[length(comparison) + 1L]] <- data.frame(
      scenario = row$scenario, outcome = row$outcome, field = field,
      python_value = py, r_value = rv, absolute_difference = abs(py - rv),
      tolerance = tolerance, pass = abs(py - rv) <= tolerance)
  }
}
checks <- do.call(rbind, comparison)
metadata_checks <- c(
  n_full_mec_design = nrow(dat) == baseline$n_full_mec_design,
  n_strata = length(psus_per_stratum) == baseline$n_strata,
  n_psus = sum(psus_per_stratum) == baseline$n_psus)
# Independently reconstruct the UNWEIGHTED pilot counts from R's imported data.
# Read expected counts from the freshly regenerated QC file: never bake the
# observed participant counts into the code, where they could conceal a change.
qc_path <- file.path(root, "outputs/tables/feasibility_summary.json")
qc <- jsonlite::fromJSON(qc_path, simplifyVector = FALSE)[["2021-2023"]]
adult <- dat[dat$complete_adult, ]
raw_positive <- adult$raw_acr >= 30
adjusted_positive <- adult$adjusted_acr >= 30
observed_counts <- c(
  n_adults_with_valid_lab = nrow(adult),
  raw_above_30 = sum(raw_positive),
  adjusted_above_30 = sum(adjusted_positive),
  cross_below_to_above = sum(!raw_positive & adjusted_positive),
  cross_above_to_below = sum(raw_positive & !adjusted_positive),
  any_reclassification = sum(raw_positive != adjusted_positive),
  clipped_adjusted_albumin = sum(adult$bridge_unclipped < 0))
expected_counts <- vapply(names(observed_counts), function(name) {
  value <- qc[[name]]
  if (is.null(value) || length(value) != 1 || !is.finite(value)) stop("Invalid QC field: ", name)
  as.numeric(value)
}, numeric(1))
qc_checks <- data.frame(field = names(observed_counts),
  python_qc_count = unname(expected_counts), r_count = unname(observed_counts),
  pass = unname(expected_counts == observed_counts))
passed <- all(checks$pass) && all(metadata_checks) && all(qc_checks$pass)

# 6. Save an auditable record, including all differences and the exact software
# versions. Source hashes identify the input files; no participant data leave R.
out <- file.path(root, "outputs/tables")
report <- file.path(root, "report")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
dir.create(report, recursive = TRUE, showWarnings = FALSE)
write.csv(r_results, file.path(out, "r_survey_results.csv"), row.names = FALSE)
write.csv(checks, file.path(out, "r_python_comparison.csv"), row.names = FALSE)
write.csv(qc_checks, file.path(out, "r_unweighted_qc_comparison.csv"), row.names = FALSE)
# Remove display padding so the reproducibility record also passes Git's
# whitespace checks when regenerated on Windows.
writeLines(trimws(capture.output(sessionInfo()), which = "right"),
           file.path(report, "r_validation_session.txt"))
status <- list(
  passed = passed, n_numeric_checks = nrow(checks), n_failed = sum(!checks$pass),
  metadata_checks = as.list(metadata_checks),
  n_unweighted_qc_checks = nrow(qc_checks), n_unweighted_qc_failed = sum(!qc_checks$pass),
  absolute_tolerance = abs_tol, relative_tolerance = rel_tol,
  maximum_absolute_difference = max(checks$absolute_difference),
  r_version = R.version.string, survey_version = as.character(packageVersion("survey")),
  source_md5 = as.list(tools::md5sum(c(demo_path, lab_path, baseline_path, qc_path))),
  generated_utc = format(Sys.time(), tz = "UTC", usetz = TRUE))
jsonlite::write_json(status, file.path(out, "r_validation_status.json"),
                     auto_unbox = TRUE, pretty = TRUE, digits = 16)
text <- c("# Independent R survey validation", "",
  paste("Result:", if (passed) "PASS" else "FAIL"), "",
  sprintf("Compared %d outcomes across six scenarios, with %d numeric checks.", nrow(r_results), nrow(checks)),
  sprintf("Failed numeric checks: %d. All design-count checks pass: %s.", sum(!checks$pass), all(metadata_checks)),
  sprintf("Unweighted QC count comparisons: %d; failures: %d. Counts are calculated from data, not hard-coded.", nrow(qc_checks), sum(!qc_checks$pass)),
  sprintf("Maximum absolute numeric difference: %.4g (proportion units for estimates and intervals).", max(checks$absolute_difference)),
  sprintf("Tolerance: %.1e + %.1e * abs(Python value); counts and degrees of freedom require exact agreement.", abs_tol, rel_tol), "",
  "R independently read the original XPT files with foreign::read.xport, rebuilt the cohort and outcomes,",
  "and estimated variances with survey::svymean. This checks data preparation and the custom Python variance calculation against a separate implementation under the shared protocol.", "",
  "## Primary results", "",
  "| Outcome | Estimate (%) or difference (percentage points) | 95% CI |",
  "|---|---:|---:|")
primary <- r_results[r_results$scenario == "primary", ]
for (i in seq_len(nrow(primary))) {
  x <- primary[i, ]
  text <- c(text, sprintf("| %s | %.5f | %.5f to %.5f |", x$outcome,
                         100 * x$estimate, 100 * x$ci95_lower, 100 * x$ci95_upper))
}
text <- c(text, "", "## Scope and limits", "",
  "Both implementations were developed within this project. Their agreement checks implementation under the shared protocol; it is not an external scientific audit, does not establish that missingness is ignorable and does not validate the assay bridge.",
  "The intervals are t Wald intervals with 15 design degrees of freedom. They condition on fixed bridge coefficients.",
  "Reporting reliability is assessed separately in report/robustness_reliability_review.md; passing that research screen is not official publication clearance.", "",
  "See r_validation_session.txt for package versions, outputs/tables/r_python_comparison.csv for every comparison,",
  "and docs/r_validation_methods.md for an explanation and rerun instructions.", "",
  "Official package reference: https://cran.r-project.org/web/packages/survey/survey.pdf")
writeLines(text, file.path(report, "r_survey_validation.md"))
print(status)
if (!passed) stop("Validation failed. Read r_python_comparison.csv; do not mark the analysis validated.")
