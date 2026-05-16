"""
Lire les datasets des Ã©lections lÃ©gislatives, europÃ©ennes, prÃ©sidentielles,
rÃ©gionales et municipales depuis 2000.
"""

from pathlib import Path
import urllib.error

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "raw"
BASE_URL = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets"


def get_datasets(force_download: bool = False) -> dict[str, pd.DataFrame]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    annees = range(2000, 2026)
    tours = ["1ertour", "2emetour"]

    datasets_ids = [
        *(f"elections-legislatives-{annee}-{tour}" for tour in tours for annee in annees),
        *(f"elections-europeennes-{annee}" for annee in annees),
        *(f"elections-presidentielles-{annee}-{tour}" for tour in tours for annee in annees),
        *(f"elections-regionales-{annee}-{tour}" for tour in tours for annee in annees),
        *(f"elections-municipales-{annee}-{tour}" for tour in tours for annee in annees),
    ]

    datasets: dict[str, pd.DataFrame] = {}

    for dataset_id in datasets_ids:
        local_path = DATA_DIR / f"{dataset_id}.parquet"
        url = f"{BASE_URL}/{dataset_id}/exports/parquet"

        try:
            if force_download or not local_path.is_file():
                print(f"downloading {dataset_id}...")
                df = pd.read_parquet(url)

                if not df.empty:
                    df.to_parquet(local_path, index=False)
                    print(f"saved to {local_path}")
                else:
                    print(f"empty dataset: {dataset_id}")
                    continue

            else:
                print(f"loading cached {dataset_id}...")
                df = pd.read_parquet(local_path)

            if not df.empty:
                print(f"{dataset_id}: {df.shape[0]} rows, {df.shape[1]} columns")
                datasets[dataset_id] = df

        except (urllib.error.HTTPError, urllib.error.URLError):
            pass

        except Exception as exc:
            print(f"failed {dataset_id}: {type(exc).__name__}: {exc}")

    return datasets


if __name__ == "__main__":
    get_datasets()
