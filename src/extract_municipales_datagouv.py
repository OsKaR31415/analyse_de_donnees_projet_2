"""
extract_municipales_datagouv.py

Extracts Paris municipal election results from the data.gouv.fr aggregated
parquet file and saves them as individual parquet files matching the existing
pipeline schema (one file per election × tour).

The pipeline cleaner (clean_election_results.py) expects wide-format files:
one row per bureau de vote, one column per candidate.  This script therefore
pivots the long-format datagouv data before writing.

Participation statistics (nb_exprim, nb_inscr) are back-calculated from the
ratio columns that datagouv provides.  nb_votant is not recoverable without
the general-results file and is left as NaN.

Input:  data/raw_datagouv/datagouv_candidats_results.parquet
Output: data/raw/elections-municipales-YEAR-Xtour.parquet  (one per tour)

Run:
    .\.venv\Scripts\python.exe .\src\extract_municipales_datagouv.py
"""

import pathlib
import numpy as np
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────

INPUT_PATH = pathlib.Path("data/raw_datagouv/datagouv_candidats_results.parquet")
OUTPUT_DIR = pathlib.Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MUNICIPAL_ELECTIONS = [
    "2008_muni_t1", "2008_muni_t2",
    "2014_muni_t1", "2014_muni_t2",
    "2020_muni_t1", "2020_muni_t2",
]

TOUR_LABEL = {"t1": "1ertour", "t2": "2emetour"}

# Columns that identify a unique polling booth × election row in wide output.
# These become id_vars for the melt in the cleaner, so they must all be present
# and must NOT look like vote columns.
BOOTH_META_COLS = [
    "id_bvote",
    "scrutin",
    "annee",
    "tour",
    "num_arrond",
    "num_bureau",
    "nb_inscr",     # back-calculated; NaN if ratio unavailable
    "nb_votant",    # not recoverable without general-results file → NaN
    "nb_exprim",    # back-calculated; required by drop_invalid_polling_rows
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_id_election(id_election: str) -> dict:
    """Parse '2020_muni_t1' → {annee: 2020, scrutin: 'Municipales', tour: 1}"""
    try:
        parts = str(id_election).split("_")
        annee = int(parts[0])
        tour = int(parts[2][1])   # 't1' → 1, 't2' → 2
        return {"annee": annee, "scrutin": "Municipales", "tour": tour}
    except Exception:
        return {"annee": None, "scrutin": "Municipales", "tour": None}


def parse_code_bv(code_bv: str) -> dict:
    """
    Parse '0101' → {num_arrond: 1, num_bureau: 1, id_bvote: '1-1'}
    Paris bureaux de vote: first 2 digits = arrondissement, last 2 = bureau number.
    """
    code_bv = str(code_bv).zfill(4)
    num_arrond = int(code_bv[:2])
    num_bureau = int(code_bv[2:])
    id_bvote = f"{num_arrond}-{num_bureau}"
    return {"num_arrond": num_arrond, "num_bureau": num_bureau, "id_bvote": id_bvote}


def build_candidate_name(row: pd.Series) -> str:
    """Build a normalised candidate column name: nom_prenom (lowercased, underscored)."""
    nom = str(row.get("nom", "") or "").strip().lower().replace(" ", "_")
    prenom = str(row.get("prenom", "") or "").strip().lower().replace(" ", "_")
    if prenom:
        return f"{nom}_{prenom}"
    return nom


def recover_booth_totals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Back-calculate nb_exprim and nb_inscr per bureau de vote from datagouv ratio
    columns (ratio_voix_exprimes, ratio_voix_inscrits), which are percentages.

    Strategy: for each bureau, use the candidate-row estimate that minimises
    rounding error — i.e. the candidate with the highest vote count, who
    contributes the most signal.  We round to the nearest integer.

    nb_votant is not recoverable without the general-results file; left as NaN.
    """
    df = df.copy()

    # Convert percentage ratios to fractions
    df["ratio_exprimes_frac"] = pd.to_numeric(df["ratio_voix_exprimes"], errors="coerce") / 100
    df["ratio_inscrits_frac"] = pd.to_numeric(df["ratio_voix_inscrits"], errors="coerce") / 100
    df["voix_num"] = pd.to_numeric(df["voix"], errors="coerce")

    # Estimate totals from each candidate row (avoid div-by-zero)
    df["est_exprim"] = np.where(
        df["ratio_exprimes_frac"] > 0,
        df["voix_num"] / df["ratio_exprimes_frac"],
        np.nan,
    )
    df["est_inscr"] = np.where(
        df["ratio_inscrits_frac"] > 0,
        df["voix_num"] / df["ratio_inscrits_frac"],
        np.nan,
    )

    # Per bureau: take the median estimate across all candidates (robust to
    # rounding outliers on very small vote counts)
    booth_key = ["id_bvote", "id_election"]
    booth_totals = (
        df.groupby(booth_key)[["est_exprim", "est_inscr"]]
        .median()
        .round()
        .astype("Int64")
        .rename(columns={"est_exprim": "nb_exprim", "est_inscr": "nb_inscr"})
        .reset_index()
    )

    return df.merge(booth_totals, on=booth_key, how="left")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Loading {INPUT_PATH} ...")
    df = pd.read_parquet(INPUT_PATH)

    # Filter to Paris municipal elections only
    paris_munic = df[
        (df["code_departement"] == "75") &
        (df["id_election"].isin(MUNICIPAL_ELECTIONS))
    ].copy()

    print(f"  Paris municipal rows found: {len(paris_munic):,}")

    # Parse bureau de vote code → arrondissement, bureau, id_bvote
    bv_parsed = paris_munic["code_bv"].apply(parse_code_bv).apply(pd.Series)
    paris_munic = pd.concat([paris_munic.reset_index(drop=True), bv_parsed], axis=1)

    # Parse election ID → scrutin, annee, tour
    election_parsed = (
        paris_munic["id_election"].astype(str)
        .apply(parse_id_election)
        .apply(pd.Series)
    )
    paris_munic = pd.concat([paris_munic.reset_index(drop=True), election_parsed], axis=1)

    # Back-calculate nb_exprim and nb_inscr from ratio columns
    paris_munic = recover_booth_totals(paris_munic)

    # Build candidate column name (used as the wide column header)
    paris_munic["candidate_col"] = paris_munic.apply(build_candidate_name, axis=1)

    # Deduplicate: if the same bureau × candidate appears more than once, sum
    # (can happen if datagouv has list-level sub-rows)
    paris_munic["voix_num"] = pd.to_numeric(paris_munic["voix"], errors="coerce").fillna(0)

    paris_munic = paris_munic.dropna(subset=["id_bvote", "candidate_col"])
    paris_munic = paris_munic[paris_munic["candidate_col"].str.strip() != ""]

    # ── Pivot to wide format ──────────────────────────────────────────────────
    # One row per bureau × election, one column per candidate.
    # This is exactly what clean_election_results.py expects.

    booth_meta = ["id_election", "id_bvote", "scrutin", "annee", "tour",
                  "num_arrond", "num_bureau", "nb_exprim", "nb_inscr"]

    # Take one metadata row per booth (values are identical across candidates)
    booth_df = (
        paris_munic[booth_meta]
        .drop_duplicates(subset=["id_election", "id_bvote"])
        .copy()
    )

    # Pivot votes: rows = booth, columns = candidate names, values = voix
    pivot = paris_munic.pivot_table(
        index=["id_election", "id_bvote"],
        columns="candidate_col",
        values="voix_num",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    pivot.columns.name = None

    wide = booth_df.merge(pivot, on=["id_election", "id_bvote"], how="left")

    # nb_votant is not recoverable without the general-results file
    wide["nb_votant"] = pd.NA

    # ── Save one parquet file per election × tour ─────────────────────────────
    for id_election in MUNICIPAL_ELECTIONS:
        subset = wide[wide["id_election"] == id_election].copy()
        subset = subset.drop(columns=["id_election"])

        if subset.empty:
            print(f"  WARNING: no rows for {id_election}, skipping.")
            continue

        year, _, tour_code = id_election.split("_")
        tour_label = TOUR_LABEL[tour_code]
        fname = f"elections-municipales-{year}-{tour_label}.parquet"
        out_path = OUTPUT_DIR / fname

        subset.to_parquet(out_path, index=False)

        n_candidates = len([c for c in subset.columns if c not in BOOTH_META_COLS])
        print(
            f"  Saved {fname}  "
            f"({len(subset):,} booths × {n_candidates} candidate columns)"
        )

    print()
    print("Done.")
    print("nb_exprim and nb_inscr were back-calculated from datagouv ratio columns.")
    print("nb_votant is NaN (not available without general-results file).")
    print("Re-run clean_election_results.py to integrate into the main pipeline.")


if __name__ == "__main__":
    main()