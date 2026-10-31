"""Hand-calculated survey examples and demographics-first denominator checks."""
import unittest
import numpy as np
import pandas as pd
from scripts.paired_analysis import survey_ratio
from scripts.pilot.audit_cohort import audit, count_demographic_adults


class SurveyTests(unittest.TestCase):
    def test_eligibility_can_be_counted_without_any_lab_columns(self):
        demo = pd.DataFrame({"RIDAGEYR": [19, 20, 70, 30],
                             "WTMEC2YR": [5., 10., 0., np.nan]})
        self.assertEqual(count_demographic_adults(demo, "WTMEC2YR"),
                         {"n_adults_demographics": 3, "n_adults_positive_mec_weight": 1})

    def test_hand_calculated_domain_variance_retains_empty_psu(self):
        # One stratum, three PSUs; third PSU has no domain members.
        # mean=1/2, PSU linear totals=(-1/4,+1/4,0), variance=3/16.
        frame = pd.DataFrame({"WTMEC2YR": [1., 1., 1.], "SDMVSTRA": [1, 1, 1], "SDMVPSU": [1, 2, 3]})
        result = survey_ratio(frame, [True, True, False], [0, 1, np.nan])
        self.assertEqual(result["estimate"], .5)
        self.assertAlmostEqual(result["standard_error"] ** 2, 3 / 16)
        self.assertEqual(result["design_df"], 2)

    def test_paired_difference_uses_within_person_outcome(self):
        frame = pd.DataFrame({"WTMEC2YR": [1., 1., 1., 1.], "SDMVSTRA": [1, 1, 2, 2], "SDMVPSU": [1, 2, 1, 2]})
        result = survey_ratio(frame, [True] * 4, [0, 0, 0, 0])
        self.assertEqual(result["estimate"], 0)
        self.assertEqual(result["standard_error"], 0)

    def test_missingness_starts_from_demographics(self):
        frame = pd.DataFrame({"RIDAGEYR": [30, 40, 50], "WTMEC2YR": [0., 1., 1.],
                              "RIDSTATR": [1, 2, 2], "URXUMA": [np.nan, np.nan, 10.],
                              "URXUCR": [np.nan, np.nan, 100.], "_merge": ["left_only", "both", "both"],
                              "RIAGENDR": [1, 1, 2], "RIDRETH3": [3, 3, 3],
                              "SDMVSTRA": [1, 1, 1], "SDMVPSU": [1, 1, 2]})
        result = audit(frame, "WTMEC2YR")
        self.assertEqual(result["n_adults_demographics"], 3)
        self.assertEqual(result["n_adults_positive_mec_weight"], 2)
        self.assertEqual(result["n_eligible_missing_or_invalid_lab"], 1)
        self.assertEqual(result["missing_or_invalid_pct_of_eligible"], 50.)
        self.assertEqual(sum(result["lab_record_categories"].values()), 2)
        self.assertEqual(result["lab_record_categories"]["both_analytes_missing_with_record"], 1)


if __name__ == "__main__":
    unittest.main()
