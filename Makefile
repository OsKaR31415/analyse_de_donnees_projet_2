
all: report presentation

.PHONY: report.py

report.py:  # update report.py according to contents of report.ipynb
	./env/bin/jupyter nbconvert --to python --no-prompt --stdout report.ipynb | grep -v "^#|" > report.py

report: report.py
	quarto render report.qmd
	echo "\007"  # ring bell at end of rendering

presentation:
	quarto render presentation.qmd
	echo "\007"  # ring bell at end of rendering




