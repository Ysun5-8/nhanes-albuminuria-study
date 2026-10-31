"""NHANES kidney assay feasibility pilot (descriptive only; not a CKD diagnosis).

Uses pandas for XPT import and SQLite for preparation. Run from the project root:
    python -m scripts.pilot.check_feasibility

No statistical modelling, hypothesis testing or ML in this pilot.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
import pandas as pd
from scripts.sql_pipeline import prepare, reclassification

# Resolve paths from this file so running from another folder is safe.
ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "outputs" / "tables"
URL_BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public"
FILES = {
    "2017-2020": ("2017", "P_ALB_CR", "P_DEMO"),
    "2021-2023": ("2021", "ALB_CR_L", "DEMO_L"),
}


def normalise_xport_zeros(frame: pd.DataFrame) -> pd.DataFrame:
    """Restore the exact IBM-XPORT zero decoded by pandas as 16**-65.

    Match this sentinel exactly; do not round small genuine concentrations.
    """
    return frame.replace(16.0 ** -65, 0.0)


def fetch_or_load(year_folder: str, stem: str) -> pd.DataFrame:
    """Read a cached XPT file, downloading it only if it is absent.

    Existing raw files are never replaced. A missing file is saved in data/raw.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / f"{stem}.xpt"
    url = f"{URL_BASE}/{year_folder}/DataFiles/{stem}.XPT"
    if not dest.exists():
        print(f"Downloading {url}")
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (reproducible research pilot)"})
        try:
            with urlopen(request, timeout=30) as response:
                data = response.read()
            if len(data) < 10000:
                raise RuntimeError(f"Unexpectedly small response for {stem}: {len(data)} bytes")
            dest.write_bytes(data)
        except (URLError, HTTPError, TimeoutError) as exc:
            raise RuntimeError(
                f"Could not download {stem}.XPT automatically ({exc}).\n"
                f"Open {url} in a browser, save the file as {dest}, then rerun."
            ) from exc
    return normalise_xport_zeros(pd.read_sas(dest, format="xport"))


def prepare_cycle(cycle: str, year: str, albumin_file: str, demo_file: str) -> pd.DataFrame:
    """Use the SQL demographics-first preparation and select complete adults."""
    weight = "WTMECPRP" if cycle == "2017-2020" else "WTMEC2YR"
    joined = prepare(fetch_or_load(year, demo_file), fetch_or_load(year, albumin_file), cycle)
    columns = ["SEQN", "URXUMA", "URXUCR", "URDACT", "RIDAGEYR", weight,
               "SDMVPSU", "SDMVSTRA", "raw_acr", "raw_positive"]
    if cycle == "2021-2023":
        columns += ["negative_adjusted_albumin", "adjusted_albumin",
                    "adjusted_acr", "adjusted_positive"]
    joined = joined.loc[joined.complete_adult, columns].copy()
    joined["cycle"] = cycle
    for column in ("raw_positive", "adjusted_positive", "negative_adjusted_albumin"):
        if column in joined:
            joined[column] = joined[column].astype(bool)
    return joined


def assess_reclassification(df: pd.DataFrame) -> dict:
    """Count paired threshold crossings without applying survey weights."""
    counts = reclassification(df)
    total = counts["n_adults_with_valid_lab"]
    counts["reclassified_pct_unweighted"] = (
        round(100 * counts["any_reclassification"] / total, 3) if total else None)
    counts["label"] = "unweighted exploratory counts, not national prevalence or clinical diagnoses"
    return counts


def main() -> None:
    """Replace feasibility_summary.json with aggregate counts for both cycles."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for cycle, (year, albumin, demo) in FILES.items():
        print(f"\nReading {cycle} NHANES...")
        df = prepare_cycle(cycle, year, albumin, demo)
        row = {
            "n_adults_with_valid_lab": len(df),
            "raw_above_30": int(df.raw_positive.sum()),
        }
        if cycle == "2021-2023":
            row = assess_reclassification(df)
            # Keep participant-level records out of the saved results.
        summary[cycle] = row
        print(json.dumps(row, indent=2))
    output = OUTPUT / "feasibility_summary.json"
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSaved summary to {output}")
    print("Descriptive feasibility counts only; cohort, missingness and survey analyses are reported separately.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"PILOT STOPPED: {error}", file=sys.stderr)
        raise SystemExit(1)
