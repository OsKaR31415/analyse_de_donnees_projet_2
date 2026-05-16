FULL EXECUTION ORDER
====================

Run from project root:


1. Download/cache OpenData Paris raw parquet files

.\.venv\Scripts\python.exe .\test_datasets.py

Output:
- data/raw/*.parquet

2. Rebuild municipal raw parquet files from data.gouv aggregate, if needed

.\.venv\Scripts\python.exe .\src\extract_municipales_datagouv.py

Input:
- data/raw_datagouv/datagouv_candidats_results.parquet

Output:
- data/raw/elections-municipales-YYYY-1ertour.parquet
- data/raw/elections-municipales-YYYY-2emetour.parquet

3. Clean non-municipal election files

.\.venv\Scripts\python.exe .\src\clean_election_results.py

Input:
- data/raw/*.parquet, excluding municipal files

Output:
- data/clean/election_results_non_municipal_long.parquet
- data/manifest/cleaning_report_non_municipal.csv

4. Clean municipal election files

.\.venv\Scripts\python.exe .\src\clean_municipal_results.py

Input:
- data/raw/elections-municipales-*.parquet

Output:
- data/clean/election_results_municipal_long.parquet
- data/manifest/cleaning_report_municipal.csv

5. Build final combined clean outputs

.\.venv\Scripts\python.exe .\src\build_clean_results.py

Inputs:
- data/clean/election_results_non_municipal_long.parquet
- data/clean/election_results_municipal_long.parquet

Outputs:
- data/clean/election_results_long.parquet
- data/clean/election_results_wide_vote_share.parquet
- data/manifest/cleaning_report.csv

6. Validate final clean outputs

.\.venv\Scripts\python.exe .\src\validate_clean_election_results.py

Inputs:
- data/clean/election_results_long.parquet
- data/clean/election_results_wide_vote_share.parquet
- data/manifest/cleaning_report.csv

Outputs:
- data/validation/validation_summary.csv
- data/validation/row_count_validation.csv
- data/validation/per_booth_vote_checks.csv
- data/validation/expressed_vote_mismatches.csv
- data/validation/municipal_row_checks.csv
- data/validation/suspicious_candidate_columns.csv
- data/validation/clean_sample.csv

7. Final strict raw-to-clean audit

.\.venv\Scripts\python.exe .\src\audit_raw_to_clean_cases.py

Inputs:
- data/raw/**/*.parquet
- data/clean/election_results_long.parquet

Outputs:
- data/audit/raw_to_clean_case_audit_summary.csv
- data/audit/raw_to_clean_case_audit_problems.csv

Expected successful final audit:
- raw_files_skipped_for_expected_cases = 0
- missing_from_clean = 0
- extra_in_clean = 0
- vote_value_mismatches = 0
- duplicate_clean_cases = 0
- duplicate_expected_cases = 0


CORE PIPELINE ONLY
==================

If raw files already exist, run only:

.\.venv\Scripts\python.exe .\src\clean_election_results.py
.\.venv\Scripts\python.exe .\src\clean_municipal_results.py
.\.venv\Scripts\python.exe .\src\build_clean_results.py
.\.venv\Scripts\python.exe .\src\validate_clean_election_results.py
.\.venv\Scripts\python.exe .\src\audit_raw_to_clean_cases.py


EXTRA METADATA / INSPECTION SCRIPTS
===================================

Run after the main pipeline:

.\.venv\Scripts\python.exe .\src\inspect_raw_datasets.py
.\.venv\Scripts\python.exe .\src\verify_parquet_metadata.py
.\.venv\Scripts\python.exe .\src\inspect_validation_problems.py

Note:
Some helper scripts were local/untracked. Notably:

src/inspect_raw_datasets.py src/verify_parquet_metadata.py src/inspect_validation_problems.py data/manifest/raw_schema_report.csv


A SUCCESSFUL RUN SUMMARY
==============================

The successful pipeline run produced:

- non-municipal clean rows: 190,413
- municipal clean rows: 29,991
- final long rows: 220,404
- final wide table: 19,748 rows × 638 columns

Final audit was fully green:

- expected_raw_candidate_cases: 220,404
- clean_long_cases: 220,404
- missing_from_clean: 0
- extra_in_clean: 0
- vote_value_mismatches: 0
- duplicate_clean_cases: 0
- duplicate_expected_cases: 0


IMPORTANT
====================

Do not skip build_clean_results.py.

clean_election_results.py and clean_municipal_results.py create separate clean files.
build_clean_results.py merges them into the final files used by validation and audit:

- data/clean/election_results_long.parquet
- data/clean/election_results_wide_vote_share.parquet
- data/manifest/cleaning_report.csv
