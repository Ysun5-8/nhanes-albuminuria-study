"""Synthetic-data checks for import, eligibility and assay-scale calculations."""
import unittest
from pathlib import Path

import pandas as pd

from scripts.pilot import check_feasibility


class PrepareCycleTests(unittest.TestCase):
    def test_xport_zero_is_restored_without_rounding_small_results(self):
        frame = pd.DataFrame({"value": [16.0 ** -65, 0.01, 1e-20, None]})
        result = check_feasibility.normalise_xport_zeros(frame)
        self.assertEqual(result.value.iloc[0], 0.0)
        self.assertEqual(result.value.iloc[1], 0.01)
        self.assertEqual(result.value.iloc[2], 1e-20)
        self.assertTrue(pd.isna(result.value.iloc[3]))

    def setUp(self):
        self.original_fetch = check_feasibility.fetch_or_load

    def tearDown(self):
        check_feasibility.fetch_or_load = self.original_fetch

    @staticmethod
    def _lab(seqn, albumin, creatinine):
        return pd.DataFrame(
            {
                "SEQN": seqn,
                "URXUMA": albumin,
                "URXUCR": creatinine,
                "URDACT": [a / c * 100.0 for a, c in zip(albumin, creatinine)],
            }
        )

    @staticmethod
    def _demo(seqn, mec_weight=1.0, include_both_weights=False):
        values = {
            "SEQN": seqn,
            "RIDAGEYR": [20] * len(seqn),
            "WTMEC2YR": [mec_weight] * len(seqn),
            "SDMVPSU": [1] * len(seqn),
            "SDMVSTRA": [1] * len(seqn),
        }
        if include_both_weights:
            values["WTMECPRP"] = [mec_weight] * len(seqn)
        return pd.DataFrame(values)

    def _mock_fetch(self, lab, demo):
        def fake_fetch(_year_folder, stem):
            return lab if "ALB" in stem else demo

        check_feasibility.fetch_or_load = fake_fetch

    def test_uses_repository_data_paths(self):
        expected_root = Path(check_feasibility.__file__).resolve().parents[2]
        self.assertEqual(check_feasibility.ROOT, expected_root)
        self.assertEqual(check_feasibility.RAW, expected_root / "data" / "raw")
        self.assertEqual(check_feasibility.OUTPUT, expected_root / "outputs" / "tables")

    def test_harmonisation_and_cycle_specific_weights(self):
        lab = self._lab([1], [30.0], [100.0])
        demo = self._demo([1], include_both_weights=True)
        self._mock_fetch(lab, demo)

        recent = check_feasibility.prepare_cycle("2021-2023", "2021", "ALB_CR_L", "DEMO_L")
        historical = check_feasibility.prepare_cycle("2017-2020", "2017", "P_ALB_CR", "P_DEMO")

        self.assertIn("WTMEC2YR", recent)
        self.assertNotIn("WTMECPRP", recent)
        self.assertIn("WTMECPRP", historical)
        self.assertNotIn("WTMEC2YR", historical)
        self.assertIn("adjusted_albumin", recent)
        self.assertIn("adjusted_positive", recent)
        self.assertNotIn("adjusted_albumin", historical)
        self.assertNotIn("adjusted_positive", historical)

    def test_raw_classification_threshold(self):
        lab = self._lab([1, 2, 3], [29.0, 30.0, 31.0], [100.0, 100.0, 100.0])
        self._mock_fetch(lab, self._demo([1, 2, 3], include_both_weights=True))

        result = check_feasibility.prepare_cycle("2017-2020", "2017", "P_ALB_CR", "P_DEMO")

        expected_uacr = [29.0, 30.0, 31.0]
        for actual, expected in zip(result["raw_acr"], expected_uacr):
            self.assertAlmostEqual(actual, expected, places=10)
        self.assertEqual(result["raw_positive"].tolist(), [False, True, True])

    def test_reclassification_and_negative_clipping(self):
        lab = self._lab([1, 2, 3], [28.0, 3.0, 0.01], [100.0, 10.0, 100.0])
        self._mock_fetch(lab, self._demo([1, 2, 3], include_both_weights=True))

        result = check_feasibility.prepare_cycle("2021-2023", "2021", "ALB_CR_L", "DEMO_L")
        summary = check_feasibility.assess_reclassification(result)

        for actual, expected in zip(result["raw_acr"], [28.0, 30.0, 0.01]):
            self.assertAlmostEqual(actual, expected, places=10)
        self.assertAlmostEqual(result.loc[result.SEQN == 1, "adjusted_albumin"].iloc[0], 31.649)
        self.assertAlmostEqual(result.loc[result.SEQN == 2, "adjusted_albumin"].iloc[0], 1.924)
        self.assertAlmostEqual(result.loc[result.SEQN == 2, "adjusted_acr"].iloc[0], 19.24)
        self.assertTrue(result.loc[result.SEQN == 3, "negative_adjusted_albumin"].iloc[0])
        self.assertEqual(result.loc[result.SEQN == 3, "adjusted_albumin"].iloc[0], 0.0)
        self.assertEqual(summary["cross_below_to_above"], 1)
        self.assertEqual(summary["cross_above_to_below"], 1)
        self.assertEqual(summary["any_reclassification"], 2)
        self.assertEqual(summary["clipped_adjusted_albumin"], 1)

    def test_excludes_missing_zero_and_negative_mec_weights(self):
        lab = self._lab([1, 2, 3, 4], [10.0, 20.0, 30.0, 40.0], [100.0] * 4)
        demo = self._demo([1, 2, 3, 4])
        demo["WTMEC2YR"] = [1.0, 0.0, None, -1.0]
        self._mock_fetch(lab, demo)

        result = check_feasibility.prepare_cycle("2021-2023", "2021", "ALB_CR_L", "DEMO_L")

        self.assertEqual(result["SEQN"].tolist(), [1])

    def test_duplicate_participant_identifiers_are_rejected(self):
        lab = self._lab([1, 1], [10.0, 20.0], [100.0, 100.0])
        self._mock_fetch(lab, self._demo([1]))

        with self.assertRaisesRegex(ValueError, "Duplicated SEQN"):
            check_feasibility.prepare_cycle("2021-2023", "2021", "ALB_CR_L", "DEMO_L")

    def test_unmatched_demographic_records_are_rejected(self):
        lab = self._lab([1], [10.0], [100.0])
        self._mock_fetch(lab, self._demo([2]))

        with self.assertRaisesRegex(ValueError, "Missing DEMO matches"):
            check_feasibility.prepare_cycle("2021-2023", "2021", "ALB_CR_L", "DEMO_L")


if __name__ == "__main__":
    unittest.main()
