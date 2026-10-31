"""Join non-urine predictors to the adult cohort and save a missingness audit."""
import hashlib
import json
import numpy as np
import pandas as pd
from scripts.pilot.check_feasibility import fetch_or_load, RAW, OUTPUT
from scripts.sql_pipeline import database, query

NUMERIC = ['age', 'bmi', 'systolic', 'diastolic']
CATEGORICAL = ['sex', 'diabetes', 'smoking']
SOURCES = {
    'body_measures': ('BMX_L', ['BMXBMI']),
    'blood_pressure': ('BPXO_L', ['BPXOSY1', 'BPXOSY2', 'BPXOSY3',
                                  'BPXODI1', 'BPXODI2', 'BPXODI3']),
    'diabetes_history': ('DIQ_L', ['DIQ010']),
    'smoking_history': ('SMQ_L', ['SMQ020', 'SMQ040']),
}


def prepare_ml():
    demo = fetch_or_load('2021', 'DEMO_L')
    lab = fetch_or_load('2021', 'ALB_CR_L')
    with database(demo, lab, '2021-2023') as con:
        for table, (stem, columns) in SOURCES.items():
            frame = fetch_or_load('2021', stem)[['SEQN'] + columns].copy()
            if not np.isfinite(frame.SEQN).all() or frame.SEQN.duplicated().any():
                raise ValueError(f'Invalid or duplicate identifiers in {stem}')
            if not frame.SEQN.isin(demo.SEQN).all():
                raise ValueError(f'Unmatched demographic records in {stem}')
            # Zero or nonfinite BMI/BP values cannot be used as measurements.
            if table in ('body_measures', 'blood_pressure'):
                frame[columns] = frame[columns].astype(float)
                frame[columns] = frame[columns].where(np.isfinite(frame[columns]) & frame[columns].gt(0))
            frame.to_sql(table, con, index=False)
            con.execute(f'CREATE UNIQUE INDEX {table}_id ON {table}(SEQN)')
        expected = con.execute('SELECT COUNT(*) FROM participants WHERE complete_adult').fetchone()[0]
        result = pd.read_sql_query(query('ml_features.sql'), con)
        if len(result) != expected or result.SEQN.duplicated().any():
            raise ValueError('Predictor joins changed the cohort')
    for column in CATEGORICAL:
        result[column] = result[column].fillna('missing')
    return result


def audit(frame):
    missing = []
    for column in NUMERIC + CATEGORICAL:
        mask = frame[column].isna() if column in NUMERIC else frame[column].eq('missing')
        missing.append({'predictor': column, 'n_missing': int(mask.sum()),
                        'pct_missing': float(100 * mask.mean())})
    stems = ['DEMO_L', 'ALB_CR_L'] + [value[0] for value in SOURCES.values()]
    result = {'n_adults': len(frame), 'n_raw_positive': int(frame.raw_label.sum()),
              'n_converted_positive': int(frame.converted_label.sum()),
              'predictors': missing,
              'source_sha256': {stem: hashlib.sha256((RAW / f'{stem}.xpt').read_bytes()).hexdigest() for stem in stems}}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'ml_data_audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    print(json.dumps(audit(prepare_ml()), indent=2))
