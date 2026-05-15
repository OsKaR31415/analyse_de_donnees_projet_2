"""
Lire les datasets des élections législatives, européennes, présidentielles, régionales et
municipales depuis 2000.
"""
import pyarrow as pa
import pandas as pd
import urllib
from os import path


def get_datasets(force_download: bool = False) -> dict[str, pd.DataFrame]:
    annees = range(2000, 2026)
    tours = ["1ertour", "2emetour"]
    datasets_ids = [*(f"elections-legislatives-{annee}-{tour}"
                      for tour in tours for annee in annees),
                    *(f"elections-europeennes-{annee}" for annee in annees),
                    *(f"elections-presidentielles-{annee}-{tour}"
                      for tour in tours for annee in annees),
                    *(f"elections-regionales-{annee}-{tour}"
                      for tour in tours for annee in annees),
                    *(f"elections-municipales-{annee}-{tour}"
                      for tour in tours for annee in annees)]
    datasets: dict[str, pd.DataFrame] = {}
    for dataset_id in datasets_ids:
        try:
            if force_reupload or not path.isfile(f"data/{dataset_id}"):
                print(f"downloading {dataset_id}...")
                df = pd.read_parquet(f"https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/{dataset_id}/exports/parquet")
            else:
                df = pd.read_parquet(f"data/{dataset_id}")
            if not df.empty:
                print(dataset_id, ":")
                print(df)
                datasets[dataset_id] = df
        except (urllib.error.HTTPError, urllib.error.URLError):
            pass
    return datasets

if __name__ == '__main__':
    get_datasets()


