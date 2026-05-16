# Cleaned election data note

This folder contains the cleaned outputs of the Paris election data pipeline.

## Main files

- `data/clean/election_results_long.parquet`
  - Main analysis dataset.
  - One row = one candidate/list result in one polling station for one election.
  - Use this for vote totals, candidate/list comparisons, regression, filtering by election/year/tour, and general analysis.

- `data/clean/election_results_wide_vote_share.parquet`
  - Wide analysis dataset.
  - One row = one polling station/election.
  - Candidate/list vote shares are stored as columns.
  - Use this for PCA, SVD, CCA, clustering, and dimensionality-reduction work.

- `data/clean/election_results_non_municipal_long.parquet`
  - Cleaned non-municipal elections only.

- `data/clean/election_results_municipal_long.parquet`
  - Cleaned municipal elections only.
  - Municipal source files are already long-format, so they are handled separately in the pipeline.

## Validation status

The final cleaned long table contains:

- 220,404 candidate-level records
- 190,413 non-municipal rows
- 29,991 municipal rows

The raw-to-clean audit reports:

- 0 missing raw candidate cases
- 0 extra clean cases
- 0 vote-value mismatches
- 0 duplicate clean cases

Municipal rows are validated separately because their source files are already long-format. For municipal data, `nb_exprim` and `nb_inscr` are reconstructed during cleaning, while `nb_votant` is allowed to be missing because it is not available in the current municipal source.

## Known source anomalies

Two non-municipal source-level consistency anomalies remain in `Présidentielle 2017 T1`:

- Bureau `12-8`: candidate votes sum to 1,177 while `nb_exprim` is 1,155.
- Bureau `13-21`: candidate votes sum to 1,227 while `nb_exprim` is 1,228.

These are retained as source-data anomalies. They are not extraction or cleaning errors.

## Recommended use

For most analysis, use:

`data/clean/election_results_long.parquet`

For PCA/SVD/clustering, use:

`data/clean/election_results_wide_vote_share.parquet`

The validation and audit files are included to document that the cleaned dataset is reliable.
