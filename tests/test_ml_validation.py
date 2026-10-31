"""Check survey-group resampling and paired metric differences."""
import importlib.util
import unittest
import numpy as np
import pandas as pd


@unittest.skipUnless(importlib.util.find_spec('sklearn'), 'Install the optional ML requirements')
class MLValidationTests(unittest.TestCase):
    def test_resampling_keeps_participants_in_the_same_psu_together(self):
        from scripts.ml.validate_models import replicate_weights
        w = np.array([1., 3., 2., 4.])
        h, j = np.array([0, 0, 0, 1]), np.array([0, 0, 1, 1])
        result = replicate_weights(w, h, j, np.array([0, 1]))
        np.testing.assert_array_equal(result, [2., 6., 0., 8.])

    def test_two_psu_mean_matches_hand_calculated_variance(self):
        from scripts.ml.validate_models import replicate_weights
        w, y = np.ones(2), np.array([0., 1.])
        estimates = [np.average(y, weights=replicate_weights(w, np.array([0, 0]),
                     np.array([0, 1]), np.array([selected]))) for selected in (0, 1)]
        self.assertEqual(np.mean((np.array(estimates) - .5) ** 2), .25)

    def test_full_design_keeps_psu_with_no_complete_adult(self):
        from scripts.ml.validate_models import design_codes
        full = pd.DataFrame({'positive_mec': [True, True], 'SDMVSTRA': [1, 1], 'SDMVPSU': [1, 2]})
        h, j, n = design_codes(full, full.iloc[:1])
        self.assertEqual(n, 1)
        np.testing.assert_array_equal(j, [0])

    def test_singleton_stratum_is_rejected(self):
        from scripts.ml.validate_models import design_codes
        full = pd.DataFrame({'positive_mec': [True], 'SDMVSTRA': [1], 'SDMVPSU': [1]})
        with self.assertRaisesRegex(ValueError, 'two PSUs'):
            design_codes(full, full)

    def test_identical_labels_have_zero_paired_metric_change(self):
        from scripts.ml.validate_models import contrasts, METRICS, MODEL_NAMES, LABELS
        values = {(model, label): {metric: .25 for metric in METRICS}
                  for model in MODEL_NAMES for label in LABELS}
        result = contrasts(values)
        for model in MODEL_NAMES:
            for metric in METRICS:
                self.assertEqual(result[(model, 'converted_minus_raw', metric)], 0.)
