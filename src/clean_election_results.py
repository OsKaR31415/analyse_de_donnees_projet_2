"""
Clean non-municipal OpenData Paris election result files.

Input:
- data/raw/*.parquet, excluding elections-municipales-*.parquet

Outputs:
- data/clean/election_results_non_municipal_long.parquet
- data/manifest/cleaning_report_non_municipal.csv

This script handles the standard wide-format election files:
one row = one polling station, candidate vote counts are columns.
"""

from pathlib import Path
import re

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifest"

LONG_OUTPUT = CLEAN_DIR / "election_results_non_municipal_long.parquet"
CLEANING_REPORT = MANIFEST_DIR / "cleaning_report_non_municipal.csv"


STANDARD_COLUMNS = {
    "raw_row_id",
    "id_bvote",
    "scrutin",
    "annee",
    "tour",
    "date",
    "num_circ",
    "num_quartier",
    "num_arrond",
    "num_bureau",
    "nb_procu",
    "nb_inscr",
    "nb_emarg",
    "nb_votant",
    "nb_bl",
    "nb_nul",
    "nb_bl_nul",
    "nb_exprim",
}

REQUIRED_RESULT_COLUMNS = {
    "id_bvote",
    "scrutin",
    "annee",
    "tour",
    "num_arrond",
    "num_bureau",
    "nb_inscr",
    "nb_votant",
    "nb_exprim",
}

COLUMN_ALIASES = {
    "id_bv": "id_bvote",
    "type_election": "scrutin",
    "numero_tour": "tour",
    "date_tour": "date",
    "circ_bv": "num_circ",
    "quartier_bv": "num_quartier",
    "arr_bv": "num_arrond",
    "nb_procuration": "nb_procu",
    "nb_inscrit": "nb_inscr",
    "nb_emargement": "nb_emarg",
    "nb_exprime": "nb_exprim",
    "nb_vote_blanc": "nb_bl",
    "nb_vote_nul": "nb_nul",
    "nb_blanc": "nb_bl",
}

SCRUTIN_CORRECTIONS = {
    "rã©guinales": "Régionales",
    "réguinales": "Régionales",
    "regionales": "Régionales",
    "régionales": "Régionales",
    "legislatives": "Législative",
    "législatives": "Législative",
    "presidentielles": "Présidentielle",
    "présidentielles": "Présidentielle",
    "présidentielle": "Présidentielle",
    "europeennes": "Européennes",
    "européennes": "Européennes",
}

NON_CANDIDATE_COLUMNS = {
    "objectid",
    "geo_shape",
    "geo_point_2d",
    "st_area_shape",
    "st_perimeter_shape",
    "created_user",
    "created_date",
    "last_edited_user",
    "last_edited_date",
    "nb_bl",
    "nb_nul",
    "nb_blanc",
    "nb_vote_blanc",
    "nb_vote_nul",
    "sec_bv",
}

STRING_COLUMNS = {
    "id_bvote",
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


def normalize_column_name(col: str) -> str:
    return str(col).strip().lower()


def apply_column_aliases(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}

    for old_name, new_name in COLUMN_ALIASES.items():
        if old_name in df.columns and new_name not in df.columns:
            rename_map[old_name] = new_name

    return df.rename(columns=rename_map)


def normalize_scrutin_values(df: pd.DataFrame) -> pd.DataFrame:
    if "scrutin" not in df.columns:
        return df

    df = df.copy()

    def _fix(value):
        if pd.isna(value):
            return pd.NA

        text = str(value).strip()
        return SCRUTIN_CORRECTIONS.get(text.lower(), text)

    df["scrutin"] = df["scrutin"].apply(_fix)
    return df


def add_combined_blank_null_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "nb_bl_nul" not in df.columns and {"nb_bl", "nb_nul"}.issubset(df.columns):
        nb_bl = pd.to_numeric(df["nb_bl"], errors="coerce").fillna(0)
        nb_nul = pd.to_numeric(df["nb_nul"], errors="coerce").fillna(0)
        df["nb_bl_nul"] = nb_bl + nb_nul

    elif "nb_bl_nul" not in df.columns and "nb_bl" in df.columns:
        df["nb_bl_nul"] = pd.to_numeric(df["nb_bl"], errors="coerce").fillna(0)

    return df


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


def is_missing_like(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip().str.lower()
    return series.isna() | text.isna() | text.isin({"", "nan", "none", "<na>"})


def replace_infinite_with_na(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.mask(~np.isfinite(numeric), pd.NA)


def drop_invalid_polling_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    before = len(df)

    id_ok = ~is_missing_like(df["id_bvote"])
    exprim_ok = pd.to_numeric(df["nb_exprim"], errors="coerce").notna()

    df = df[id_ok & exprim_ok].copy()

    dropped = before - len(df)
    return df, dropped


def looks_like_vote_column(series: pd.Series) -> bool:
    numeric = pd.to_numeric(series, errors="coerce")
    non_missing_ratio = numeric.notna().mean()

    return non_missing_ratio >= 0.80


def detect_candidate_columns(df: pd.DataFrame, metadata_cols: list[str]) -> list[str]:
    candidate_cols = []

    for col in df.columns:
        if col in metadata_cols:
            continue

        if col in NON_CANDIDATE_COLUMNS:
            continue

        if looks_like_vote_column(df[col]):
            candidate_cols.append(col)

    return candidate_cols


def clean_one_file(file_path: Path) -> tuple[pd.DataFrame | None, dict]:
    df = pd.read_parquet(file_path)
    df.columns = [normalize_column_name(col) for col in df.columns]
    df["raw_row_id"] = range(len(df))

    df = apply_column_aliases(df)
    df = normalize_scrutin_values(df)
    df = add_combined_blank_null_column(df)

    report = {
        "file": str(file_path.relative_to(PROJECT_ROOT)),
        "rows_raw": len(df),
        "columns_raw": len(df.columns),
        "status": "ok",
        "reason": "",
    }

    missing_required = REQUIRED_RESULT_COLUMNS - set(df.columns)

    if missing_required:
        report["status"] = "skipped"
        report["reason"] = f"missing required columns: {sorted(missing_required)}"
        return None, report

    df, dropped_rows = drop_invalid_polling_rows(df)

    report["rows_after_key_filter"] = len(df)
    report["rows_dropped_missing_keys"] = dropped_rows

    metadata_cols = [col for col in df.columns if col in STANDARD_COLUMNS]
    candidate_cols = detect_candidate_columns(df, metadata_cols)

    if not candidate_cols:
        report["status"] = "skipped"
        report["reason"] = "no candidate columns detected"
        return None, report

    long_df = df.melt(
        id_vars=metadata_cols,
        value_vars=candidate_cols,
        var_name="candidate_source_column",
        value_name="votes",
    )

    long_df["candidate"] = long_df["candidate_source_column"]
    long_df["source_file"] = file_path.name
    long_df["dataset_id"] = file_path.stem

    long_df["votes"] = pd.to_numeric(long_df["votes"], errors="coerce").fillna(0)
    long_df["nb_exprim"] = pd.to_numeric(long_df["nb_exprim"], errors="coerce")
    long_df["nb_inscr"] = pd.to_numeric(long_df["nb_inscr"], errors="coerce")

    long_df["vote_share_exprimes"] = replace_infinite_with_na(
        long_df["votes"] / long_df["nb_exprim"]
    )
    long_df["vote_share_registered"] = replace_infinite_with_na(
        long_df["votes"] / long_df["nb_inscr"]
    )

    long_df = long_df[long_df["candidate"].notna()].copy()
    long_df = normalize_output_types(long_df)

    report["rows_clean_long"] = len(long_df)
    report["candidate_columns"] = len(candidate_cols)
    report["candidate_column_names"] = " | ".join(candidate_cols)

    return long_df, report


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    parquet_files = [
        p
        for p in sorted(RAW_DIR.rglob("*.parquet"))
        if not p.name.startswith("elections-municipales-")
    ]

    if not parquet_files:
        print(f"No non-municipal raw parquet files found in {RAW_DIR}")
        return

    cleaned_frames = []
    reports = []

    for file_path in parquet_files:
        try:
            clean_df, report = clean_one_file(file_path)
            reports.append(report)

            if clean_df is not None:
                cleaned_frames.append(clean_df)
                print(f"[ok] {file_path.name}: {len(clean_df)} cleaned rows")
            else:
                print(f"[skip] {file_path.name}: {report['reason']}")

        except Exception as exc:
            reports.append(
                {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "rows_raw": pd.NA,
                    "columns_raw": pd.NA,
                    "status": "error",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
            print(f"[error] {file_path.name}: {exc}")

    report_df = pd.DataFrame(reports)
    report_df.to_csv(CLEANING_REPORT, index=False, encoding="utf-8-sig")

    if not cleaned_frames:
        print("No non-municipal election result files could be cleaned.")
        return

    long_df = pd.concat(cleaned_frames, ignore_index=True)
    long_df = normalize_output_types(long_df)
    long_df.to_parquet(LONG_OUTPUT, index=False)

    print()
    print(f"[ok] Non-municipal long table written to: {LONG_OUTPUT.relative_to(PROJECT_ROOT)}")
    print(f"[ok] Cleaning report written to: {CLEANING_REPORT.relative_to(PROJECT_ROOT)}")
    print("Non-municipal long table shape:", long_df.shape)


if __name__ == "__main__":
    main()