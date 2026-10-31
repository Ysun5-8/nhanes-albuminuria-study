"""Reconcile SQL flow with the audit; optionally compare pre-migration outputs.

Run after all Python entry points. --baseline is a directory containing the
three original aggregate JSON files, never participant-level data.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from scripts.pilot.check_feasibility import OUTPUT

FILES = ('mec_missingness_audit.json', 'feasibility_summary.json',
         'paired_survey_analysis.json')


def compare(old, new, path='', counts=None):
    if counts is None:
        counts = {'numeric_values': 0, 'other_values': 0}
    if isinstance(old, dict):
        if old.keys() != new.keys():
            raise AssertionError(f'Different keys at {path}')
        for key in old:
            compare(old[key], new[key], f'{path}/{key}', counts)
    elif isinstance(old, list):
        if len(old) != len(new):
            raise AssertionError(f'Different lengths at {path}')
        for i, (a, b) in enumerate(zip(old, new)):
            compare(a, b, f'{path}/{i}', counts)
    elif isinstance(old, (int, float)) and not isinstance(old, bool):
        if not math.isclose(old, new, rel_tol=1e-12, abs_tol=1e-12):
            raise AssertionError(f'Different values at {path}: {old} vs {new}')
        counts['numeric_values'] += 1
    else:
        if old != new:
            raise AssertionError(f'Different value at {path}')
        counts['other_values'] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    flow = json.loads((OUTPUT / 'sql_cohort_flow.json').read_text())
    audit = json.loads((OUTPUT / FILES[0]).read_text())
    pilot = json.loads((OUTPUT / FILES[1]).read_text())
    survey = json.loads((OUTPUT / FILES[2]).read_text())
    checked = 0
    for cycle, row in flow['cycles'].items():
        for key in ('n_adults_demographics', 'n_adults_positive_mec_weight',
                    'n_eligible_valid_lab', 'n_eligible_missing_or_invalid_lab',
                    'n_eligible_no_lab_row'):
            if row[key] != audit['cycles'][cycle][key]:
                raise AssertionError(f'SQL/audit mismatch: {cycle}/{key}')
            checked += 1
        if row['n_eligible_valid_lab'] != pilot[cycle]['n_adults_with_valid_lab']:
            raise AssertionError(f'SQL/pilot mismatch: {cycle}')
        checked += 1
    if flow['cycles']['2021-2023']['n_full_mec_design'] != survey['n_full_mec_design']:
        raise AssertionError('Full survey design mismatch')
    checked += 1
    result = {'passed': True, 'flow_checks': checked,
              'comparison_tolerance': {'relative': 1e-12, 'absolute': 1e-12},
              'baseline_comparisons': {}}
    if args.baseline:
        for name in FILES:
            original = (args.baseline / name).read_bytes()
            current = json.loads((OUTPUT / name).read_text())
            counts = compare(json.loads(original), current)
            result['baseline_comparisons'][name] = {
                'baseline_sha256': hashlib.sha256(original).hexdigest(), **counts}
    target = OUTPUT / ('sql_migration_validation.json' if args.baseline else 'sql_integration_checks.json')
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
