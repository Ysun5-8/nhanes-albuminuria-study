"""Check questionnaire skips and missing blood pressure readings."""
import unittest
from unittest.mock import patch
import pandas as pd
from scripts.ml.prepare_data import prepare_ml


class MLPredictorTests(unittest.TestCase):
    def setUp(self):
        ids = [1., 2., 3., 4.]
        self.sources = {
            'DEMO_L': pd.DataFrame({'SEQN': ids, 'RIDAGEYR': [40.] * 4,
                'RIAGENDR': [1., 2., 1., 2.], 'WTMEC2YR': [1.] * 4,
                'SDMVSTRA': [1.] * 4, 'SDMVPSU': [1., 1., 2., 2.]}),
            'ALB_CR_L': pd.DataFrame({'SEQN': ids, 'URXUMA': [10.] * 4,
                'URXUCR': [100.] * 4, 'URDACT': [10.] * 4}),
            'BMX_L': pd.DataFrame({'SEQN': ids, 'BMXBMI': [25.] * 4}),
            'BPXO_L': pd.DataFrame({'SEQN': ids, 'BPXOSY1': [100., None, 0., None],
                'BPXOSY2': [120., None, 120., None], 'BPXOSY3': [None] * 4,
                'BPXODI1': [70.] * 4, 'BPXODI2': [80.] * 4, 'BPXODI3': [None] * 4}),
            'DIQ_L': pd.DataFrame({'SEQN': ids, 'DIQ010': [1., 2., 3., 9.]}),
            'SMQ_L': pd.DataFrame({'SEQN': ids, 'SMQ020': [2., 1., 1., 9.],
                'SMQ040': [None, 3., 2., None]}),
        }

    def prepare(self):
        with patch('scripts.ml.prepare_data.fetch_or_load',
                   side_effect=lambda year, stem: self.sources[stem].copy()):
            return prepare_ml()

    def test_smoking_skip_is_not_missing_for_never_smokers(self):
        self.assertEqual(self.prepare().smoking.tolist(), ['never', 'former', 'current', 'missing'])

    def test_diabetes_borderline_is_separate_from_unknown(self):
        self.assertEqual(self.prepare().diabetes.tolist(), ['yes', 'no', 'borderline', 'missing'])

    def test_bp_mean_uses_only_available_positive_readings(self):
        frame = self.prepare()
        self.assertEqual(frame.systolic.iloc[0], 110.)
        self.assertTrue(pd.isna(frame.systolic.iloc[1]))
        self.assertEqual(frame.systolic.iloc[2], 120.)
        self.assertTrue(pd.isna(frame.systolic.iloc[3]))
        self.assertEqual(frame.diastolic.tolist(), [75.] * 4)

    def test_missing_predictor_record_keeps_participant(self):
        self.sources['BMX_L'] = self.sources['BMX_L'].iloc[:3]
        frame = self.prepare()
        self.assertEqual(len(frame), 4)
        self.assertTrue(pd.isna(frame.bmi.iloc[3]))

    def test_duplicate_predictor_record_fails(self):
        self.sources['BMX_L'] = pd.concat([self.sources['BMX_L']] * 2)
        with self.assertRaisesRegex(ValueError, 'duplicate identifiers'):
            self.prepare()
