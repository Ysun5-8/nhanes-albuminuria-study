"""Paired domain ratios with stratified PSU Taylor linearisation.

Run: python -m scripts.paired_analysis
All positive-weight MEC records remain in the design, including nonadults.
"""
import json
import numpy as np
from scipy.stats import t

from scripts.pilot.audit_cohort import join_cycle
from scripts.pilot.check_feasibility import OUTPUT


def survey_ratio(frame, domain, outcome, weight="WTMEC2YR"):
    """With-replacement first-stage variance of a domain weighted mean.

    Linearised individual values = w * I(domain) * (y - mean) / sum(w*I).
    Sum by PSU, then sum m/(m-1) * squared deviations within strata.
    """
    # People outside the domain stay in the design with zero contribution.
    # This preserves the PSU structure needed for subgroup uncertainty.
    w = frame[weight].to_numpy(dtype=float)
    domain = np.asarray(domain, dtype=bool)
    y = np.asarray(outcome, dtype=float)
    if (not np.isfinite(w).all() or (w <= 0).any()
            or frame[["SDMVSTRA", "SDMVPSU"]].isna().any().any()):
        raise ValueError("Invalid survey design")
    if not np.isfinite(y[domain]).all() or not domain.any():
        raise ValueError("Empty domain or invalid domain outcomes")
    denominator = w[domain].sum()
    estimate = float(np.dot(w[domain], y[domain]) / denominator)
    linear = np.zeros(len(frame))
    linear[domain] = w[domain] * (y[domain] - estimate) / denominator
    work = frame[["SDMVSTRA", "SDMVPSU"]].copy()
    work["linear"] = linear
    psu = work.groupby(["SDMVSTRA", "SDMVPSU"]).linear.sum()
    variance, degrees = 0.0, 0
    for _, totals in psu.groupby(level=0):
        m = len(totals)
        if m < 2:
            raise ValueError("Singleton PSU stratum; explicit handling required")
        variance += m / (m - 1) * float(((totals - totals.mean()) ** 2).sum())
        degrees += m - 1
    se = float(np.sqrt(variance))
    margin = float(t.ppf(0.975, degrees) * se)
    return {"estimate": estimate, "standard_error": se,
            "ci95_lower": estimate - margin, "ci95_upper": estimate + margin,
            "design_df": degrees, "n_domain": int(domain.sum())}


def analyse(frame, domain, raw, adjusted):
    """Estimate six outcomes on the same participants and survey design."""
    # Subtract indicators within each person to retain their covariance.
    outcomes = {
        "raw_at_or_above_30": raw,
        "harmonised_at_or_above_30": adjusted,
        "paired_difference_harmonised_minus_raw": adjusted.astype(float) - raw.astype(float),
        "any_reclassification": raw != adjusted,
        "below_to_above": ~raw & adjusted,
        "above_to_below": raw & ~adjusted,
    }
    return {name: survey_ratio(frame, domain, value) for name, value in outcomes.items()}


def main():
    """Write aggregate primary results and sensitivities; replace existing output."""
    frame = join_cycle("2021-2023")
    frame = frame.loc[frame.positive_mec].copy()
    domain = frame.complete_adult
    raw_acr, adjusted_acr = frame.raw_acr, frame.adjusted_acr
    converted = frame.bridge_unclipped
    # Missing urine is outside the domain; false here is only an array placeholder.
    raw = frame.raw_positive.fillna(0).astype(bool)
    adjusted = frame.adjusted_positive.fillna(0).astype(bool)
    primary = analyse(frame, domain, raw, adjusted)
    # Bound missing-outcome impact among all adult MEC participants without
    # assuming their true classification or treating missing values as observed.
    adult = frame.RIDAGEYR.ge(20)
    missing = adult & ~domain
    adult_weight = frame.loc[adult, "WTMEC2YR"].sum()
    bounds = {}
    for label, outcome in [("raw", raw), ("harmonised", adjusted)]:
        lower = frame.loc[domain & outcome, "WTMEC2YR"].sum() / adult_weight
        bounds[label] = {"lower": float(lower), "upper": float(lower + frame.loc[missing, "WTMEC2YR"].sum() / adult_weight)}
    results = {
        "cycle": "August 2021-August 2023", "units": "proportions; multiply by 100 for percent or percentage points",
        "method": "Domain ratio, with-replacement stratified PSU Taylor linearization; two-sided t Wald 95% CI; no FPC",
        "interpretation": "Complete urine-data adults with MEC weights; national interpretation assumes ignorable residual urine nonresponse. Single specimen, not CKD diagnosis. Bridge coefficients treated as fixed.",
        "n_full_mec_design": len(frame),
        "n_strata": int(frame.SDMVSTRA.nunique()),
        "n_psus": len(frame.groupby(["SDMVSTRA", "SDMVPSU"])),
        "primary": primary,
        "sensitivity": {
            "exclude_below_detection_either_analyte": analyse(frame, domain & frame.URDUMALC.eq(0) & frame.URDUCRLC.eq(0), raw, adjusted),
            "exclude_negative_bridge_values": analyse(frame, domain & converted.ge(0), raw, adjusted),
            "strictly_greater_than_30": analyse(frame, domain, raw_acr.gt(30), adjusted_acr.gt(30)),
            "published_rounded_raw_URDACT": analyse(frame, domain & frame.URDACT.notna(), frame.URDACT.ge(30), adjusted),
            "unclipped_bridge": analyse(frame, domain, raw, (converted / frame.URXUCR * 100).ge(30)),
        },
        "missing_outcome_prevalence_bounds_no_ci": bounds,
        "limitations": ["Wald intervals, especially for rare directional changes, are approximate; check NCHS presentation standards before publication.", "No item nonresponse reweighting or bridge-parameter uncertainty propagation.", "Sensitivity exclusions change the target domain; they are not interchangeable national estimates."],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "paired_survey_analysis.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(primary, indent=2))


if __name__ == "__main__":
    main()
