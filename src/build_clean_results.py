"""
Build final clean election result tables.

Inputs:
- data/clean/election_results_non_municipal_long.parquet
- data/clean/election_results_municipal_long.parquet

Outputs:
- data/clean/election_results_long.parquet
- data/clean/election_results_wide_vote_share.parquet
- data/manifest/cleaning_report.csv
"""

from pathlib import Path
import re

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifest"

NON_MUNICIPAL_LONG = CLEAN_DIR / "election_results_non_municipal_long.parquet"
MUNICIPAL_LONG = CLEAN_DIR / "election_results_municipal_long.parquet"

FINAL_LONG = CLEAN_DIR / "election_results_long.parquet"
FINAL_WIDE = CLEAN_DIR / "election_results_wide_vote_share.parquet"

NON_MUNICIPAL_REPORT = MANIFEST_DIR / "cleaning_report_non_municipal.csv"
MUNICIPAL_REPORT = MANIFEST_DIR / "cleaning_report_municipal.csv"
FINAL_REPORT = MANIFEST_DIR / "cleaning_report.csv"


STRING_COLUMNS = {
    "id_bvote",
    "source_bv_id",
    "scrutin",
    "tour",
    "num_circ",
    "num_quartier",
    "num_arrond",
    "num_bureau",
    "candidate",
    "candidate_source_column",
    "source_file",
    "dataset_id",
    "nom",
    "prenom",
    "nuance",
    "liste",
}

NUMERIC_COLUMNS = {
    "raw_row_id",
    "nb_procu",
    "nb_inscr",
    "nb_emarg",
    "nb_votant",
    "nb_bl",
    "nb_nul",
    "nb_bl_nul",
    "nb_exprim",
    "votes",
    "vote_share_exprimes",
    "vote_share_registered",
}


def extract_year(value) -> int | None:
    if pd.isna(value):
        return None

    match = re.search(r"(20\d{2})", str(value))
    if not match:
        return None

    return int(match.group(1))


def normalize_output_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "annee" in df.columns:
        df["annee"] = df["annee"].apply(extract_year).astype("Int64")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
        df["date"] = df["date"].dt.date.astype("string")

    for col in STRING_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("string")

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    return df


def build_wide_vote_share_table(long_df: pd.DataFrame) -> pd.DataFrame:
    index_cols = [
        "dataset_id",
        "source_file",
        "id_bvote",
        "source_bv_id",
        "scrutin",
        "annee",
        "tour",
        "date",
        "num_circ",
        "num_quartier",
        "num_arrond",
        "num_bureau",
        "nb_inscr",
        "nb_votant",
        "nb_exprim",
    ]

    index_cols = [col for col in index_cols if col in long_df.columns]

    work = long_df[index_cols + ["candidate", "vote_share_exprimes"]].copy()

    missing_marker = "__MISSING_INDEX_VALUE__"

    for col in index_cols:
        work[col] = work[col].astype("object")
        work[col] = work[col].where(work[col].notna(), missing_marker)

    grouped = (
        work.groupby(index_cols + ["candidate"], as_index=False, dropna=False)[
            "vote_share_exprimes"
        ]
        .sum()
    )

    wide = grouped.pivot(
        index=index_cols,
        columns="candidate",
        values="vote_share_exprimes",
    ).fillna(0).reset_index()

    wide.columns.name = None

    for col in index_cols:
        wide[col] = wide[col].replace(missing_marker, pd.NA)

    wide = normalize_output_types(wide)

    return wide


def build_combined_cleaning_report() -> None:
    report_frames = []

    if NON_MUNICIPAL_REPORT.exists():
        report_frames.append(pd.read_csv(NON_MUNICIPAL_REPORT))

    if MUNICIPAL_REPORT.exists():
        report_frames.append(pd.read_csv(MUNICIPAL_REPORT))

    if not report_frames:
        print("[warn] No cleaning reports found to combine.")
        return

    report_df = pd.concat(report_frames, ignore_index=True)
    report_df.to_csv(FINAL_REPORT, index=False, encoding="utf-8-sig")

    print(f"[ok] Combined cleaning report written to: {FINAL_REPORT.relative_to(PROJECT_ROOT)}")


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    missing_inputs = [
        p for p in [NON_MUNICIPAL_LONG, MUNICIPAL_LONG]
        if not p.exists()
    ]

    if missing_inputs:
        print("[error] Missing required clean input files:")
        for p in missing_inputs:
            print("  -", p.relative_to(PROJECT_ROOT))
        print()
        print("Run these first:")
        print(r"  .\.venv\Scripts\python.exe .\src\clean_election_results.py")
        print(r"  .\.venv\Scripts\python.exe .\src\clean_municipal_results.py")
        return

    non_municipal = pd.read_parquet(NON_MUNICIPAL_LONG)
    municipal = pd.read_parquet(MUNICIPAL_LONG)

    long_df = pd.concat([non_municipal, municipal], ignore_index=True, sort=False)
    long_df = normalize_output_types(long_df)
    long_df.to_parquet(FINAL_LONG, index=False)

    print(f"[ok] Final long table written to: {FINAL_LONG.relative_to(PROJECT_ROOT)}")
    print("Final long table shape:", long_df.shape)

    wide_df = build_wide_vote_share_table(long_df)
    wide_df.to_parquet(FINAL_WIDE, index=False)

    print(f"[ok] Final wide table written to: {FINAL_WIDE.relative_to(PROJECT_ROOT)}")
    print("Final wide table shape:", wide_df.shape)

    build_combined_cleaning_report()

    print()
    print("Coverage:")
    coverage = (
        long_df[["dataset_id", "scrutin", "annee", "tour"]]
        .drop_duplicates()
        .sort_values(["scrutin", "annee", "tour", "dataset_id"])
    )
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()