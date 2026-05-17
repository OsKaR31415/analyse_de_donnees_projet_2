"""Matrix factorization utilities for the election analysis report.
The project stores cleaned election results in a wide table where one row is a
polling station in one election and candidate/list vote shares are columns. This
module keeps the PCA/SVD and CCA computations reusable from both scripts and
Quarto notebooks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WIDE_CSV = PROJECT_ROOT / "data" / "clean" / "csv" / "election_results_wide_vote_share.csv"

META_COLUMNS = {
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
}


@dataclass(frozen=True)
class PCAResult:
    """Container for PCA/SVD outputs."""

    scores: pd.DataFrame
    loadings: pd.DataFrame
    explained_variance_ratio: pd.DataFrame
    feature_means: pd.Series
    feature_stds: pd.Series


@dataclass(frozen=True)
class CCAResult:
    """Container for CCA outputs."""

    joined_scores: pd.DataFrame
    x_weights: pd.DataFrame
    y_weights: pd.DataFrame
    correlations: pd.DataFrame


def load_wide_results(path: Path | str = WIDE_CSV) -> pd.DataFrame:
    """Load the cleaned wide vote-share table from CSV."""

    return pd.read_csv(path, low_memory=False)


def candidate_columns(df: pd.DataFrame) -> list[str]:
    """Return numeric candidate/list vote-share columns."""

    cols: list[str] = []
    for col in df.columns:
        if col in META_COLUMNS:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            cols.append(col)
    return cols


def election_matrix(
    df: pd.DataFrame,
    dataset_id: str,
    *,
    min_total_share: float = 0.002,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return metadata and candidate vote-share matrix for one election.
    Candidate columns that are zero everywhere for the selected election are
    removed. A small total-share threshold also removes one-off lists that add
    little signal but can make the PCA loading plot unreadable.
    """

    election = df.loc[df["dataset_id"] == dataset_id].copy()
    if election.empty:
        raise ValueError(f"Unknown dataset_id: {dataset_id}")

    cols = candidate_columns(election)
    X = election[cols].fillna(0.0)
    active_cols = X.columns[X.sum(axis=0) >= min_total_share].tolist()
    X = X[active_cols]

    metadata = election[[col for col in META_COLUMNS if col in election.columns]].copy()
    return metadata, X


def _standardize(X: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    means = X.mean(axis=0)
    stds = X.std(axis=0, ddof=1).replace(0, 1.0)
    Z = (X - means) / stds
    return Z, means, stds


def pca_svd(
    df: pd.DataFrame,
    dataset_id: str,
    *,
    n_components: int = 4,
    min_total_share: float = 0.002,
) -> PCAResult:
    """Compute PCA using an explicit singular value decomposition."""

    metadata, X = election_matrix(df, dataset_id, min_total_share=min_total_share)
    Z, means, stds = _standardize(X)

    U, singular_values, Vt = np.linalg.svd(Z.to_numpy(), full_matrices=False)
    n_components = min(n_components, Vt.shape[0])
    component_names = [f"PC{i}" for i in range(1, n_components + 1)]

    scores = pd.DataFrame(
        U[:, :n_components] * singular_values[:n_components],
        columns=component_names,
        index=metadata.index,
    )
    scores = pd.concat([metadata.reset_index(drop=True), scores.reset_index(drop=True)], axis=1)

    loadings = pd.DataFrame(
        Vt[:n_components, :].T,
        columns=component_names,
        index=X.columns,
    )
    loadings.index.name = "candidate"
    loadings = loadings.reset_index()

    eigenvalues = singular_values**2 / (len(Z) - 1)
    explained = eigenvalues / eigenvalues.sum()
    explained_df = pd.DataFrame(
        {
            "component": [f"PC{i}" for i in range(1, len(explained) + 1)],
            "explained_variance_ratio": explained,
            "cumulative_variance_ratio": np.cumsum(explained),
        }
    )

    return PCAResult(
        scores=scores,
        loadings=loadings,
        explained_variance_ratio=explained_df,
        feature_means=means,
        feature_stds=stds,
    )


def strongest_loadings(loadings: pd.DataFrame, component: str, n: int = 8) -> pd.DataFrame:
    """Return the strongest positive and negative loadings for one component."""

    cols = ["candidate", component]
    ordered = loadings[cols].assign(abs_loading=lambda d: d[component].abs())
    return ordered.sort_values("abs_loading", ascending=False).head(n).drop(columns="abs_loading")


def arrondissement_component_summary(scores: pd.DataFrame) -> pd.DataFrame:
    """Average PCA coordinates by arrondissement for spatial summaries."""

    return (
        scores.dropna(subset=["num_arrond"])
        .groupby("num_arrond", as_index=False)
        .agg(
            PC1=("PC1", "mean"),
            PC2=("PC2", "mean"),
            polling_stations=("id_bvote", "nunique"),
            mean_registered=("nb_inscr", "mean"),
        )
        .sort_values("num_arrond")
    )


def cca_compare(
    df: pd.DataFrame,
    left_dataset_id: str,
    right_dataset_id: str,
    *,
    n_components: int = 3,
    min_total_share: float = 0.002,
    ridge: float = 1e-8,
) -> CCAResult:
    """Compare two elections with canonical correlation analysis.

    The two election matrices are joined on polling-station id. CCA is computed
    from whitened covariance matrices using SVD, which avoids adding another
    dependency for a small amount of linear algebra.
    """

    left_meta, X = election_matrix(df, left_dataset_id, min_total_share=min_total_share)
    right_meta, Y = election_matrix(df, right_dataset_id, min_total_share=min_total_share)

    x_join_cols = [f"x__{col}" for col in X.columns]
    y_join_cols = [f"y__{col}" for col in Y.columns]
    left_values = X.reset_index(drop=True).copy()
    left_values.columns = x_join_cols
    right_values = Y.reset_index(drop=True).copy()
    right_values.columns = y_join_cols

    left = pd.concat([left_meta[["id_bvote", "num_arrond"]].reset_index(drop=True), left_values], axis=1)
    right = pd.concat([right_meta[["id_bvote", "num_arrond"]].reset_index(drop=True), right_values], axis=1)
    joined = left.merge(right, on="id_bvote", suffixes=("_left", "_right"))
    if joined.empty:
        raise ValueError(f"No common polling stations between {left_dataset_id} and {right_dataset_id}")

    x_cols = X.columns.tolist()
    y_cols = Y.columns.tolist()
    Xj = joined[x_join_cols].fillna(0.0)
    Yj = joined[y_join_cols].fillna(0.0)

    Xz, _, _ = _standardize(Xj)
    Yz, _, _ = _standardize(Yj)
    Xn = Xz.to_numpy()
    Yn = Yz.to_numpy()
    n = len(joined)

    Sxx = (Xn.T @ Xn) / (n - 1) + ridge * np.eye(Xn.shape[1])
    Syy = (Yn.T @ Yn) / (n - 1) + ridge * np.eye(Yn.shape[1])
    Sxy = (Xn.T @ Yn) / (n - 1)

    eig_x, vec_x = np.linalg.eigh(Sxx)
    eig_y, vec_y = np.linalg.eigh(Syy)
    inv_sqrt_x = vec_x @ np.diag(1.0 / np.sqrt(np.maximum(eig_x, ridge))) @ vec_x.T
    inv_sqrt_y = vec_y @ np.diag(1.0 / np.sqrt(np.maximum(eig_y, ridge))) @ vec_y.T

    whitened = inv_sqrt_x @ Sxy @ inv_sqrt_y
    U, canonical_corrs, Vt = np.linalg.svd(whitened, full_matrices=False)
    n_components = min(n_components, len(canonical_corrs))
    component_names = [f"CC{i}" for i in range(1, n_components + 1)]

    x_weights_array = inv_sqrt_x @ U[:, :n_components]
    y_weights_array = inv_sqrt_y @ Vt.T[:, :n_components]

    X_scores = Xn @ x_weights_array
    Y_scores = Yn @ y_weights_array
    score_df = pd.DataFrame(
        {
            "id_bvote": joined["id_bvote"],
            "num_arrond": joined.get("num_arrond_left", joined.get("num_arrond")),
        }
    )
    for i, name in enumerate(component_names):
        score_df[f"{name}_left"] = X_scores[:, i]
        score_df[f"{name}_right"] = Y_scores[:, i]

    x_weights = pd.DataFrame(x_weights_array, columns=component_names, index=x_cols)
    x_weights.index.name = "candidate"
    y_weights = pd.DataFrame(y_weights_array, columns=component_names, index=y_cols)
    y_weights.index.name = "candidate"

    correlations = pd.DataFrame(
        {
            "component": component_names,
            "canonical_correlation": canonical_corrs[:n_components],
        }
    )

    return CCAResult(
        joined_scores=score_df,
        x_weights=x_weights.reset_index(),
        y_weights=y_weights.reset_index(),
        correlations=correlations,
    )


def available_elections(df: pd.DataFrame) -> pd.DataFrame:
    """Return the election rounds available in the clean wide table."""

    return (
        df[["dataset_id", "scrutin", "annee", "tour"]]
        .drop_duplicates()
        .sort_values(["scrutin", "annee", "tour", "dataset_id"])
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    wide = load_wide_results()
    print(available_elections(wide).to_string(index=False))
