"""Prepare participant records for the audit and survey analysis.

Pandas reads the XPT files. SQL joins the tables and calculates the study variables.
The database stays in memory and closes after each query run.
"""
from contextlib import contextmanager
from pathlib import Path
import math
import sqlite3

import pandas as pd

SQL = Path(__file__).resolve().parents[1] / 'sql'
WEIGHTS = {'2017-2020': 'WTMECPRP', '2021-2023': 'WTMEC2YR'}


def query(name):
    return (SQL / name).read_text(encoding='utf-8')


def identifier(value):
    """Quote a column name so spaces or quotes do not break the SQL."""
    return '"' + value.replace('"', '""') + '"'


@contextmanager
def connection():
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    # SQL needs the same finite-value check as the survey analysis.
    con.create_function('is_finite', 1,
                        lambda x: int(x is not None and math.isfinite(x)),
                        deterministic=True)
    try:
        yield con
    finally:
        con.close()


@contextmanager
def database(demo, lab, cycle):
    """Check participant IDs, then build the joined SQL views."""
    weight = WEIGHTS[cycle]
    required = {'SEQN', 'RIDAGEYR', weight, 'SDMVSTRA', 'SDMVPSU'}
    for frame, columns, label in [(demo, required, 'DEMO'),
                                  (lab, {'SEQN', 'URXUMA', 'URXUCR', 'URDACT'}, 'LAB')]:
        if columns - set(frame):
            raise ValueError(f'{label} lacks {sorted(columns - set(frame))}')
    overlap = (set(demo) & set(lab)) - {'SEQN'}
    if overlap:
        raise ValueError(f'Ambiguous shared columns: {sorted(overlap)}')
    with connection() as con:
        demo.to_sql('demographics', con, index=False)
        lab.to_sql('urine', con, index=False)
        for table in ('demographics', 'urine'):
            invalid = con.execute(f'SELECT COUNT(*) FROM {table} WHERE NOT is_finite(SEQN)').fetchone()[0]
            duplicate = con.execute(f'SELECT SEQN FROM {table} GROUP BY SEQN HAVING COUNT(*) > 1 LIMIT 1').fetchone()
            if invalid:
                raise ValueError(f'Missing or nonfinite SEQN in {table}')
            if duplicate:
                raise ValueError(f'Duplicated SEQN in {table}')
            con.execute(f'CREATE UNIQUE INDEX {table}_seqn ON {table}(SEQN)')
        unmatched = con.execute('SELECT COUNT(*) FROM urine l LEFT JOIN demographics d ON l.SEQN=d.SEQN WHERE d.SEQN IS NULL').fetchone()[0]
        if unmatched:
            raise ValueError(f'Missing DEMO matches: {unmatched}')
        lab_columns = ', '.join('l.' + identifier(c) for c in lab if c != 'SEQN')
        con.executescript(query('prepare_participants.sql').format(
            weight=identifier(weight), cycle=cycle, lab_columns=lab_columns))
        if con.execute('SELECT COUNT(*) FROM participants').fetchone()[0] != len(demo):
            raise ValueError('Laboratory join changed the demographic denominator')
        yield con


def prepare(demo, lab, cycle):
    with database(demo, lab, cycle) as con:
        result = pd.read_sql_query('SELECT * FROM participants ORDER BY SEQN', con)
        result.attrs['sql_cohort_flow'] = dict(con.execute(query('cohort_flow.sql')).fetchone())
    for column in ('is_adult', 'positive_mec', 'valid_urine', 'complete_adult'):
        result[column] = result[column].astype(bool)
    # Missing urine remains unclassified.
    return result


def reclassification(frame):
    with connection() as con:
        frame.to_sql('analysis_sample', con, index=False)
        return dict(con.execute(query('reclassification.sql')).fetchone())


def missingness_groups(frame, weight):
    if weight not in WEIGHTS.values():
        raise ValueError('Unknown MEC weight')
    # Rebuild the flags so this audit can also check a plain joined table.
    with connection() as con:
        frame = frame.drop(columns=['is_adult', 'positive_mec', 'valid_urine', 'age_group'], errors='ignore')
        frame.to_sql('source', con, index=False)
        con.executescript('''CREATE VIEW participants AS SELECT *,
            COALESCE(RIDAGEYR >= 20, 0) AS is_adult,
            (is_finite({w}) AND {w} > 0) AS positive_mec,
            (is_finite(URXUMA) AND URXUMA >= 0 AND is_finite(URXUCR)
                AND URXUCR > 0) AS valid_urine,
            CASE WHEN RIDAGEYR >= 60 THEN '60+' WHEN RIDAGEYR >= 40
                THEN '40-59' WHEN RIDAGEYR >= 20 THEN '20-39' END AS age_group
            FROM source;'''.format(w=identifier(weight)))
        groups = {}
        for column in ('age_group', 'RIAGENDR', 'RIDRETH3'):
            rows = con.execute(query('missingness_by_demographics.sql').format(
                group=identifier(column), weight=identifier(weight))).fetchall()
            groups[column] = {}
            for row in rows:
                values = dict(row)
                label = values.pop('group_label')
                groups[column]['nan' if label is None else str(label)] = values
        return groups


def main():
    import json
    from scripts.pilot.check_feasibility import FILES, OUTPUT, fetch_or_load
    result = {'engine': 'SQLite', 'sqlite_version': sqlite3.sqlite_version, 'cycles': {}}
    for cycle, (year, lab, demo) in FILES.items():
        frame = prepare(fetch_or_load(year, demo), fetch_or_load(year, lab), cycle)
        result['cycles'][cycle] = frame.attrs['sql_cohort_flow']
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'sql_cohort_flow.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
