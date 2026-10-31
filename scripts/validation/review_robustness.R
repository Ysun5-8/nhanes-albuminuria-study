# Run: Rscript scripts/validation/review_robustness.R <project-root>
# This review builds on the independently validated R cohort and outcomes.
# Sourcing the validator first ensures every run rechecks agreement with Python.
# Sourcing the validator also replaces its outputs before this review runs.
# The variables dat, r_results, design_df, out and report come from it.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("Supply the project root")
root <- normalizePath(args[1], winslash = "/", mustWork = TRUE)
source(file.path(root, "scripts/validation/validate_with_r.R"), local = TRUE)
source(file.path(root, "scripts/validation/reliability_helpers.R"), local = TRUE)

# 1. Reporting screen for the five binary primary outcomes. The paired change
# is a mean of -1/0/+1 and must not be screened as a binomial proportion.
raw <- dat$raw_acr >= 30
adjusted <- dat$adjusted_acr >= 30
dat$raw <- as.numeric(raw)
dat$harmonised <- as.numeric(adjusted)
dat$upward <- as.numeric(!raw & adjusted)
dat$downward <- as.numeric(raw & !adjusted)
dat$reclassified <- as.numeric(raw != adjusted)
dat$paired_change <- dat$harmonised - dat$raw
dat$missing_urine <- as.numeric(!dat$complete_adult)
dat$age_group <- cut(dat$RIDAGEYR, c(20, 40, 60, Inf), right = FALSE,
                     labels = c("20-39", "40-59", "60+"))
dat$sex <- factor(dat$RIAGENDR, levels = c(1, 2), labels = c("Male", "Female"))
dat$race_ethnicity <- factor(dat$RIDRETH3, levels = c(1, 2, 3, 4, 6, 7),
  labels = c("Mexican American", "Other Hispanic", "Non-Hispanic White",
           "Non-Hispanic Black", "Non-Hispanic Asian", "Other/multiracial"))
design <- make_design(dat)
adults_design <- subset(design, RIDAGEYR >= 20)
complete_design <- subset(design, complete_adult)
binary <- c("raw", "harmonised", "upward", "downward", "reclassified")
reliability <- list()
for (outcome in binary) {
  formula <- reformulate(outcome)
  estimate <- svymean(formula, complete_design)
  p <- unname(coef(estimate)[1])
  v <- unname(vcov(estimate)[1, 1])
  y <- complete_design$variables[[outcome]]
  n <- length(y)
  events <- sum(y)
  kg <- kg_interval(p, v, n, df = design_df)
  # Package beta interval is also saved. It may differ if n_eff > n because
  # our presentation interval caps the effective denominator at actual n.
  package_beta <- confint(svyciprop(formula, complete_design, method = "beta"))
  logit <- confint(svyciprop(formula, complete_design, method = "logit", df = design_df))
  if (kg$used<n) stopifnot(max(abs(c(kg$lower, kg$upper) - package_beta))<1e-10)
  psu_key <- interaction(complete_design$variables$SDMVSTRA, complete_design$variables$SDMVPSU, drop = TRUE)
  reliability[[outcome]] <- data.frame(
    outcome = outcome, n = n, events = events, event_psus = length(unique(psu_key[y == 1])),
    estimate = p, standard_error = sqrt(v), rse_pct = 100 * sqrt(v) / p,
    effective_n = kg$neff, effective_n_used = kg$used, design_df = design_df,
    kg_lower = kg$lower, kg_upper = kg$upper,
    kg_width_pp = 100 * (kg$upper - kg$lower), kg_relative_width_pct = 100 * (kg$upper - kg$lower) / p,
    package_beta_lower = package_beta[1], package_beta_upper = package_beta[2],
    logit_t_lower = logit[1], logit_t_upper = logit[2],
    screen = presentation_screen(p, n, kg$size_neff, kg$lower, kg$upper, design_df, events),
    complement_screen = presentation_screen(1 - p, n, kg$size_neff, 1 - kg$upper, 1 - kg$lower, design_df, n - events))
}
reliability <- do.call(rbind, reliability)
write.csv(reliability, file.path(out, "reporting_reliability.csv"), row.names = FALSE)

# 2. Quantify missingness by available demographics. Rates and t Wald intervals
# are descriptive; no p-value threshold is used to declare missingness ignorable.
missing_rows <- list()
for (variable in c("age_group", "sex", "race_ethnicity")) {
  for (level in levels(adults_design$variables[[variable]])) {
    selected <- adults_design$variables[[variable]] == level
    group <- adults_design[selected & !is.na(selected), ]
    fit <- svymean( ~ missing_urine, group)
    ci <- confint(fit, df = design_df)
    missing_rows[[length(missing_rows) + 1]] <- data.frame(
      variable = variable, level = level, n = nrow(group$variables),
      missing = sum(group$variables$missing_urine), rate = unname(coef(fit)[1]),
      ci_lower = ci[1], ci_upper = ci[2])
  }
}
missing_table <- do.call(rbind, missing_rows)
write.csv(missing_table, file.path(out, "missingness_demographic_review.csv"), row.names = FALSE)

# 3. Missing-not-at-random stress test for the paired difference itself.
# q is the mean harmonised-minus-raw indicator among missing-data adults.
# No model identifies q from the observed data. Show a range rather than
# claiming that the primary CI accounts for missing outcomes.
adult_mask <- dat$RIDAGEYR >= 20
missing_share <- sum(dat$WTMEC2YR[adult_mask & !dat$complete_adult]) / sum(dat$WTMEC2YR[adult_mask])
observed <- unname(coef(svymean( ~ paired_change, complete_design))[1])
q <- c( - 1, - .5, - .25, 0, .25, .5, 1)
stress <- data.frame(missing_group_mean_paired_change = q,
  all_examined_adult_paired_change = (1 - missing_share) * observed + missing_share * q)
write.csv(stress, file.path(out, "paired_missingness_stress_test.csv"), row.names = FALSE)
bounds <- paired_missing_bounds(observed, missing_share)
tipping_q <- - (1 - missing_share) * observed / missing_share

# 4. Transparent response-cell weighting sensitivity (age x sex x race).
# Within each demographic cell, multiply complete-data MEC weights by the
# ratio of ALL adult MEC-weight mass to RESPONDENT weight mass. This assumes
# outcomes are exchangeable between respondents/nonrespondents within cells.
# postStratify propagates the calibration through survey variance estimation.
# The target totals themselves are estimated from this MEC sample and treated
# as fixed here: intervals are conditional diagnostics, not definitive MAR CIs.
dat$response_cell <- interaction(dat$age_group, dat$sex, dat$race_ethnicity, drop = TRUE)
adult_dat <- dat[adult_mask, ]
if (anyNA(adult_dat$response_cell)) stop("Missing response-cell demographics")
targets <- aggregate(WTMEC2YR ~ response_cell, data = adult_dat, FUN = sum)
names(targets)[2] <- "Freq"
respondent_mass <- aggregate(WTMEC2YR ~ response_cell, data = dat[dat$complete_adult, ], FUN = sum)
cell_check <- merge(targets, respondent_mass, by = "response_cell", all.x = TRUE)
if (anyNA(cell_check$WTMEC2YR) || any(cell_check$WTMEC2YR <= 0)) stop("Cell without respondents")
cell_check$weight_multiplier <- cell_check$Freq / cell_check$WTMEC2YR
write.csv(cell_check, file.path(out, "response_cell_weighting_diagnostics.csv"), row.names = FALSE)
response_design <- subset(make_design(dat), complete_adult)
adjusted_design <- postStratify(response_design, ~ response_cell, targets)
adjusted_fit <- svymean( ~ raw + harmonised + paired_change + reclassified, adjusted_design)
adjusted_ci <- confint(adjusted_fit, df = design_df)
response_results <- data.frame(outcome = names(coef(adjusted_fit)),
  estimate = unname(coef(adjusted_fit)), se = unname(SE(adjusted_fit)),
  ci_lower = adjusted_ci[, 1], ci_upper = adjusted_ci[, 2], row.names = NULL)
write.csv(response_results, file.path(out, "response_weighting_sensitivity.csv"), row.names = FALSE)

# 5. Build the readable results table from outputs, with explicit interval
# labels: original t Wald primary results versus KG reporting-screen intervals.
primary_rows <- r_results[r_results$scenario == "primary", ]
text <- c("# Robustness and reporting-reliability review", "",
  "## Validated primary results", "",
  "| Outcome | Estimate (% or percentage points) | Original t Wald 95% CI |",
  "|---|---:|---:|")
for (i in seq_len(nrow(primary_rows))) {
  x <- primary_rows[i, ]
  text <- c(text, sprintf("| %s | %.4f | %.4f to %.4f |", x$outcome, 100 * x$estimate, 100 * x$ci95_lower, 100 * x$ci95_upper))
}
text <- c(text, "", "## Proportion reporting screen", "",
  "| Outcome | Events | Effective n used | KG 95% CI (%) | Screen |",
  "|---|---:|---:|---:|---|")
for (i in seq_len(nrow(reliability))) {
  x <- reliability[i, ]
  text <- c(text, sprintf("| %s | %d | %.1f | %.4f to %.4f | %s |", x$outcome, x$events, x$effective_n_used, 100 * x$kg_lower, 100 * x$kg_upper, x$screen))
}
down <- reliability[reliability$outcome == "downward", ]
text <- c(text, "",
  sprintf("Downward reclassification occurs in %d participants across %d PSUs. RSE is %.1f%%; KG relative interval width is %.1f%%, but absolute width is only %.3f percentage points.", down$events, down$event_psus, down$rse_pct, down$kg_relative_width_pct, down$kg_width_pp),
  "A small nonzero numerator does not itself trigger suppression. The downward estimate remains sparse despite passing the screen; the event count and interval are reported without further subgroup analysis.",
  "This is a transparent research reporting screen, not NCHS publication clearance. It uses effective-n beta intervals with the survey 4.5 finite-design-df adjustment and caps the interval denominator at actual n; complements are also checked. Finite-df logit intervals are saved as an additional sensitivity. The paired difference is not a binomial proportion, so these size/width rules are not applied to it.",
  "", "## Missing-outcome robustness", "",
  sprintf("Missing urine results account for %.3f%% of adult MEC weight. Their unknown mean paired change would need to be %.3f (%.1f percentage points) to bring the overall point difference to zero.", 100 * missing_share, tipping_q, 100 * tipping_q),
  sprintf("Allowing that missing-group mean to range over [-1,1] gives all-examined-adult paired-change bounds of %.3f to %.3f percentage points. These are worst-case identification bounds, not confidence limits.", 100 * bounds[1], 100 * bounds[2]),
  "The observed positive change is not guaranteed under unrestricted missingness. These bounds do not assert that the most extreme assignments are plausible.",
  sprintf("Age/sex/race response-cell weighting gives a paired difference of %.3f percentage points, versus %.3f before response adjustment. Largest cell weight multiplier: %.3f.", 100 * response_results$estimate[response_results$outcome == "paired_change"], 100 * observed, max(cell_check$weight_multiplier)),
  "The response-cell analysis assumes exchangeability within cells. Its confidence intervals condition on estimated target totals; it cannot resolve nonignorable missingness.",
  "", "## Assay and threshold sensitivities", "",
  "| Sensitivity | Complete-data n | Paired change (percentage points) | t Wald 95% CI |",
  "|---|---:|---:|---:|")
sens <- r_results[r_results$scenario != "primary" & r_results$outcome == "paired_difference_harmonised_minus_raw", ]
for(i in seq_len(nrow(sens))) {
  x <- sens[i, ]
  text <- c(text, sprintf("| %s | %d | %.3f | %.3f to %.3f |", x$scenario, x$n_domain, 100 * x$estimate, 100 * x$ci95_lower, 100 * x$ci95_upper))
}
text <- c(text, "", "## Descriptive missingness by demographics", "",
  "| Demographic | Group | Missing / examined | Weighted missing (%) |",
  "|---|---|---:|---:|")
for(i in seq_len(nrow(missing_table))) {
  x <- missing_table[i, ]
  text <- c(text, sprintf("| %s | %s | %d / %d | %.3f |", x$variable, x$level, x$missing, x$n, 100 * x$rate))
}
text <- c(text, "",
  "These descriptive differences do not establish that missingness is ignorable. See the saved CSV for design-based intervals; subgroup intervals are not used as a missing-data mechanism test.",
  "", "## Interpretation", "",
  "The primary finding is the paired increase among adults with complete urine data. Response weighting, worst-case missing-outcome bounds and assay/threshold sensitivities describe its dependence on the analysis assumptions. Sampling confidence intervals exclude bridge uncertainty and missing-data bias. Single urine measurements do not diagnose CKD.",
  "", "## Reproduction and references", "",
  "Run Rscript scripts/validation/review_robustness.R <project-root>. Run Rscript tests/test_reliability_helpers.R <project-root> for helper checks. All CSV outputs are aggregates in outputs/tables/; no raw data are modified.",
  "NCHS proportion standards: https://www.cdc.gov/nchs/data/series/sr_02/sr02_175.pdf",
  "NHANES reliability tutorial: https://wwwn.cdc.gov/nchs/nhanes/tutorials/reliabilityofestimates.aspx",
  "R survey methods: https://cran.r-project.org/web/packages/survey/survey.pdf")
writeLines(text, file.path(report, "robustness_reliability_review.md"))
jsonlite::write_json(list(missing_weight_share = missing_share,
  paired_missing_bounds = as.list(bounds), missing_group_tipping_mean = tipping_q,
  screen_results = as.list(setNames(reliability$screen, reliability$outcome)),
  n_response_cells = nrow(cell_check), largest_response_weight_multiplier = max(cell_check$weight_multiplier)),
  file.path(out, "robustness_review_summary.json"), auto_unbox = TRUE, pretty = TRUE, digits = 16)
writeLines(trimws(capture.output(sessionInfo()), which = "right"), file.path(report, "robustness_review_session.txt"))
cat("Saved robustness and reliability report.\n")
