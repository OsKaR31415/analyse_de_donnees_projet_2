$ErrorActionPreference = "Stop"

$PY = ".\.venv\Scripts\python.exe"

Write-Host "`n[1/8] Downloading non-municipal OpenData Paris files..."
& $PY .\src\get_data\download\fetch_non_municipal_data.py

Write-Host "`n[2/8] Downloading data.gouv.fr candidate results..."
& $PY .\src\get_data\download\download_datagouv_candidats_results.py

Write-Host "`n[3/8] Extracting municipal data.gouv.fr files..."
& $PY .\src\get_data\download\extract_municipales_datagouv.py

Write-Host "`n[4/8] Cleaning non-municipal results..."
& $PY .\src\get_data\clean\clean_election_results.py

Write-Host "`n[5/8] Cleaning municipal results..."
& $PY .\src\get_data\clean\clean_municipal_results.py

Write-Host "`n[6/8] Building final clean results..."
& $PY .\src\get_data\clean\build_clean_results.py

Write-Host "`n[7/8] Validating clean results..."
& $PY .\src\get_data\validation\validate_clean_election_results.py

Write-Host "`n[8/8] Auditing raw-to-clean cases..."
& $PY .\src\get_data\audit\audit_raw_to_clean_cases.py

Write-Host "`n[ok] Full pipeline completed."