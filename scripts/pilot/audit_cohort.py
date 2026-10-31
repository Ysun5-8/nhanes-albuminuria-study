"""Demographics-first MEC eligibility and urine missingness audit."""
import json
import numpy as np

from scripts.pilot.check_feasibility import FILES, OUTPUT, fetch_or_load
from scripts.sql_pipeline import prepare, missingness_groups


def join_cycle(cycle):
    """Join laboratories onto demographics without losing eligible adults."""
    year, lab_name, demo_name = FILES[cycle]
    demo = fetch_or_load(year, demo_name)
    # Count examination eligibility before the laboratory join.
    # Examination counts include adults with missing specimens.
    weight = "WTMECPRP" if cycle == "2017-2020" else "WTMEC2YR"
    before_join = count_demographic_adults(demo, weight)
    lab = fetch_or_load(year, lab_name)
    joined = prepare(demo, lab, cycle)
    if count_demographic_adults(joined, weight) != before_join:
        raise ValueError("Laboratory join changed the demographic denominator")
    joined.attrs["adults_before_lab_join"] = before_join
    return joined


def count_demographic_adults(demo, weight):
    """Use demographics alone; this function does not need any lab columns."""
    adults = demo.loc[demo.RIDAGEYR.ge(20)]
    return {"n_adults_demographics": len(adults),
            "n_adults_positive_mec_weight": int((np.isfinite(adults[weight]) & adults[weight].gt(0)).sum())}


def valid_lab(frame):
    """Require finite albumin >=0 and finite creatinine >0 for the ratio."""
    return (np.isfinite(frame.URXUMA) & frame.URXUMA.ge(0)
            & np.isfinite(frame.URXUCR) & frame.URXUCR.gt(0))


def audit(frame, weight):
    """Separate examination exclusions from missing urine results in adults.

    Age, sex and race/ethnicity summaries describe response patterns; they
    do not establish that the missing outcomes are ignorable.
    """
    adults = frame.loc[frame.RIDAGEYR.ge(20)].copy()
    positive = np.isfinite(adults[weight]) & adults[weight].gt(0)
    examined = adults.RIDSTATR.eq(2)
    if (positive != examined).any():
        raise ValueError("Positive MEC weight disagrees with examination status")
    eligible = adults.loc[positive].copy()
    valid = valid_lab(eligible)
    patterns = {}
    for albumin_missing, creatinine_missing in [(True, True), (True, False), (False, True), (False, False)]:
        mask = (eligible.URXUMA.isna().eq(albumin_missing)
                & eligible.URXUCR.isna().eq(creatinine_missing))
        patterns[f"albumin_missing_{albumin_missing}_creatinine_missing_{creatinine_missing}"] = int(mask.sum())
    groups = missingness_groups(frame, weight)
    return {
        "n_adults_demographics": len(adults),
        "n_adults_positive_mec_weight": int(positive.sum()),
        "n_adults_interview_only": int(adults.RIDSTATR.eq(1).sum()),
        "n_adults_missing_mec_weight": int(adults[weight].isna().sum()),
        "n_adults_zero_mec_weight": int(adults[weight].eq(0).sum()),
        "n_adults_negative_mec_weight": int(adults[weight].lt(0).sum()),
        "n_eligible_no_lab_row": int(eligible._merge.eq("left_only").sum()),
        # These categories are mutually exclusive. Missing-analyte counts below
        # concern existing lab rows; absent rows are reported separately.
        "lab_record_categories": {
            "no_lab_record": int(eligible._merge.eq("left_only").sum()),
            "both_analytes_missing_with_record": int((eligible._merge.eq("both") & eligible.URXUMA.isna() & eligible.URXUCR.isna()).sum()),
            "albumin_only_missing_with_record": int((eligible._merge.eq("both") & eligible.URXUMA.isna() & eligible.URXUCR.notna()).sum()),
            "creatinine_only_missing_with_record": int((eligible._merge.eq("both") & eligible.URXUMA.notna() & eligible.URXUCR.isna()).sum()),
            "both_analytes_present_valid": int(valid.sum()),
            "both_analytes_present_invalid": int((eligible.URXUMA.notna() & eligible.URXUCR.notna() & ~valid).sum()),
        },
        "n_eligible_valid_lab": int(valid.sum()),
        "n_eligible_missing_or_invalid_lab": int((~valid).sum()),
        "missing_or_invalid_pct_of_eligible": float(100 * (~valid).mean()),
        "weighted_missing_or_invalid_pct_of_eligible": float(100 * eligible.loc[~valid, weight].sum() / eligible[weight].sum()),
        "n_eligible_nonmissing_invalid_albumin": int((eligible.URXUMA.notna() & (~np.isfinite(eligible.URXUMA) | eligible.URXUMA.lt(0))).sum()),
        "n_eligible_nonmissing_invalid_creatinine": int((eligible.URXUCR.notna() & (~np.isfinite(eligible.URXUCR) | eligible.URXUCR.le(0))).sum()),
        "n_eligible_missing_design": int(eligible[["SDMVSTRA", "SDMVPSU"]].isna().any(axis=1).sum()),
        "missingness_patterns_among_eligible": patterns,
        "missingness_by_demographics": groups,
    }


def main():
    """Replace mec_missingness_audit.json with aggregate flow and missingness."""
    result = {"scope": "Unweighted cohort flow and descriptive weighted missingness; age >=20", "cycles": {}}
    for cycle in FILES:
        weight = "WTMECPRP" if cycle == "2017-2020" else "WTMEC2YR"
        joined = join_cycle(cycle)
        result["cycles"][cycle] = audit(joined, weight)
        result["cycles"][cycle]["demographics_before_lab_join"] = joined.attrs["adults_before_lab_join"]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "mec_missingness_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
