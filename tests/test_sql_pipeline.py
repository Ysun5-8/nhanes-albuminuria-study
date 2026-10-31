"""Boundary cases for SQL joins, NULL handling and domain preservation."""
import unittest
import numpy as np
import pandas as pd
from scripts.sql_pipeline import prepare, reclassification


class SQLPreparationTests(unittest.TestCase):
    def setUp(self):
        self.demo = pd.DataFrame({
            'SEQN': [1., 2., 3., 4.], 'RIDAGEYR': [19., 20., 40., 60.],
            'WTMEC2YR': [1., 1., 1., 0.], 'SDMVSTRA': [1.] * 4,
            'SDMVPSU': [1., 1., 2., 2.]})
        self.lab = pd.DataFrame({'SEQN': [1., 2., 4.], 'URXUMA': [30., 28., 10.],
                                 'URXUCR': [100.] * 3, 'URDACT': [30., 28., 10.]})

    def test_left_join_preserves_children_and_absent_specimens(self):
        out = prepare(self.demo, self.lab, '2021-2023')
        self.assertEqual(out.SEQN.tolist(), [1., 2., 3., 4.])
        self.assertEqual(out.positive_mec.tolist(), [True, True, True, False])
        self.assertEqual(out.complete_adult.tolist(), [False, True, False, False])
        missing = out.loc[out.SEQN.eq(3)].iloc[0]
        self.assertEqual(missing['_merge'], 'left_only')
        self.assertTrue(pd.isna(missing.raw_positive))
        self.assertTrue(pd.isna(missing.adjusted_positive))
        self.assertEqual(out.attrs['sql_cohort_flow']['n_eligible_no_lab_row'], 1)

    def test_invalid_concentrations_are_not_negative_outcomes(self):
        for albumin, creatinine in [(np.inf, 100.), (-1., 100.), (10., 0.),
                                     (10., np.inf), (np.nan, 100.)]:
            with self.subTest(albumin=albumin, creatinine=creatinine):
                self.lab.loc[1, ['URXUMA', 'URXUCR']] = [albumin, creatinine]
                out = prepare(self.demo, self.lab, '2021-2023')
                row = out.loc[out.SEQN.eq(2)].iloc[0]
                self.assertFalse(row.complete_adult)
                self.assertTrue(pd.isna(row.raw_acr))
                self.assertTrue(pd.isna(row.adjusted_positive))

    def test_nonfinite_weights_cannot_enter_design(self):
        self.demo.WTMEC2YR = [np.inf, -np.inf, np.nan, 0.]
        out = prepare(self.demo, self.lab, '2021-2023')
        self.assertFalse(out.positive_mec.any())
        self.assertFalse(out.complete_adult.any())

    def test_null_identifier_is_rejected(self):
        self.lab.loc[0, 'SEQN'] = np.nan
        with self.assertRaisesRegex(ValueError, 'Missing or nonfinite SEQN'):
            prepare(self.demo, self.lab, '2021-2023')

    def test_ambiguous_columns_are_rejected(self):
        self.lab['RIDAGEYR'] = 20.
        with self.assertRaisesRegex(ValueError, 'Ambiguous shared columns'):
            prepare(self.demo, self.lab, '2021-2023')

    def test_historical_cycle_is_not_converted(self):
        self.demo = self.demo.rename(columns={'WTMEC2YR': 'WTMECPRP'})
        out = prepare(self.demo, self.lab, '2017-2020')
        self.assertTrue(out.adjusted_acr.isna().all())
        self.assertTrue(out.adjusted_positive.isna().all())

    def test_empty_reclassification_returns_zero_counts(self):
        frame = pd.DataFrame(columns=['raw_positive', 'adjusted_positive',
                                      'negative_adjusted_albumin'])
        self.assertTrue(all(value == 0 for value in reclassification(frame).values()))


if __name__ == '__main__':
    unittest.main()
