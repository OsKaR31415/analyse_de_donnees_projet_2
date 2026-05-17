
all: report
.PHONY: report.py
report.py:  
	jupyter nbconvert --to python --no-prompt --stdout report.ipynb | grep -v "^#|" > report.py
report:
	quarto render report.qmd
	echo "\007" 
presentation:
	quarto render presentation.qmd
	echo "\007" 
