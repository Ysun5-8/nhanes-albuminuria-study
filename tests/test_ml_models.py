"""Check model inputs and training-only preprocessing."""
import importlib.util
import unittest
import numpy as np
import pandas as pd


@unittest.skipUnless(importlib.util.find_spec('sklearn'), 'Install the optional ML requirements')
class MLModelTests(unittest.TestCase):
    def test_preprocessing_uses_training_median(self):
        from scripts.ml.run_models import models
        train = pd.DataFrame({'age': [20., 40., 60., 80.], 'bmi': [20., 30., np.nan, 40.],
            'systolic': [120.] * 4, 'diastolic': [80.] * 4,
            'sex': ['male', 'female'] * 2, 'diabetes': ['no'] * 4, 'smoking': ['never'] * 4})
        preprocess = models()['logistic'].named_steps['prepare']
        preprocess.fit(train)
        test = train.iloc[:1].copy()
        test.bmi = 10000.
        preprocess.transform(test)
        imputer = preprocess.named_transformers_['numeric'].named_steps['impute']
        self.assertEqual(imputer.statistics_[1], 30.)

    def test_predictor_list_excludes_outcomes_and_design_columns(self):
        from scripts.ml.prepare_data import NUMERIC, CATEGORICAL
        self.assertEqual(set(NUMERIC + CATEGORICAL),
                         {'age', 'bmi', 'systolic', 'diastolic', 'sex', 'diabetes', 'smoking'})

    def test_weighted_probability_metrics(self):
        from scripts.ml.run_models import metrics
        result = metrics(np.array([0, 1]), np.array([.25, .75]), np.array([1., 3.]))
        self.assertAlmostEqual(result['brier'], .0625)
        self.assertAlmostEqual(result['prevalence'], .75)
        self.assertAlmostEqual(result['mean_prediction'], .625)
        self.assertEqual(result['roc_auc'], 1.)
