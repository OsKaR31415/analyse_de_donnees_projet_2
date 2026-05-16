PYTHON ?= ./.venv/Scripts/python.exe

.PHONY: all report.py report presentation get_data/download clean validate audit pipeline

all: report presentation

report.py:
	jupyter nbconvert --to python --no-prompt --stdout report.ipynb | grep -v "^#|" > report.py

report: report.py
	quarto render report.qmd
	echo "\007"

presentation:
	quarto render presentation.qmd
	echo "\007"

get_data/download:
	$(PYTHON) src/get_data/download/fetch_non_municipal_data.py
	$(PYTHON) src/get_data/download/download_datagouv_candidats_results.py
	$(PYTHON) src/get_data/download/extract_municipales_datagouv.py

clean:
	$(PYTHON) src/get_data/clean/clean_election_results.py
	$(PYTHON) src/get_data/clean/clean_municipal_results.py
	$(PYTHON) src/get_data/clean/build_clean_results.py

validate:
	$(PYTHON) src/get_data/validation/validate_clean_election_results.py

audit:
	$(PYTHON) src/get_data/audit/audit_raw_to_clean_cases.py

pipeline: get_data/download clean validate audit