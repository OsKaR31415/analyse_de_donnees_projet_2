PYTHON3=./env/bin/python3

all: report presentation

# .PHONY: report.py

report.py:  report.ipynb # update report.py according to contents of report.ipynb
	./env/bin/jupyter nbconvert --to python --no-prompt --stdout report.ipynb | grep -v "^#|" > report.py

report: report.py
	quarto render report.qmd
	echo "\007"  # ring bell at end of rendering

presentation:
	quarto render presentation.qmd
	echo "\007"  # ring bell at end of rendering



# GETTING DATA

get_data/download:
	${PYTHON3} src/get_data/download/extract_municipales_datagouv.py
	${PYTHON3} src/get_data/download/fetch_non_municipal_data.py

get_data/clean:
	${PYTHON3} src/get_data/clean/clean_election_results.py
	${PYTHON3} src/get_data/clean/clean_municipal_results.py
	${PYTHON3} src/get_data/clean/build_clean_results.py

audit-and-validate-data:
	${PYTHON3} src/get_data/validation/validate_clean_election_results.py
	${PYTHON3} src/get_data/audit/audit_raw_to_clean_cases.py
	${PYTHON3} src/get_data/inspect/inspect_raw_datasets.py
	${PYTHON3} src/get_data/inspect/verify_parquet_metadata.py
	${PYTHON3} src/get_data/validation/inspect_validation_problems.py


get_data: get_data/download get_data/clean get_data/audit-and-validate-data


