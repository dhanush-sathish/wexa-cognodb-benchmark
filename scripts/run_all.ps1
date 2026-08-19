# Orchestrates the full benchmark: dataset prep -> load every platform ->
# run every workload -> collect footprint -> regenerate README results tables.
#
# Prerequisites:
#   1. python -m venv .venv ; .venv\Scripts\Activate.ps1 ; pip install -r requirements.txt
#   2. Copy .env.example to .env and fill in COGNODB_URI / COGNODB_PASSWORD
#      (from your own CognoDB Cloud signup -- see README.md section "Setup").
#   3. docker compose up -d   (starts neo4j, memgraph, falkordb, arangodb,
#      each capped to the same 0.5 vCPU / 512MB as CognoDB's free tier)
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts/run_all.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "=== 1. Preparing dataset ===" -ForegroundColor Cyan
python "$root/data/prepare_dataset.py"

Write-Host "=== 2. Loading data into every platform ===" -ForegroundColor Cyan
python "$root/src/loaders/load_cypher_family.py" --platform cognodb
python "$root/src/loaders/load_cypher_family.py" --platform neo4j
python "$root/src/loaders/load_cypher_family.py" --platform memgraph
python "$root/src/loaders/load_falkordb.py"
python "$root/src/loaders/load_arangodb.py"

Write-Host "=== 3. Running workloads on every platform ===" -ForegroundColor Cyan
python "$root/src/workloads/run_cypher_family.py" --platform cognodb
python "$root/src/workloads/run_cypher_family.py" --platform neo4j
python "$root/src/workloads/run_cypher_family.py" --platform memgraph
python "$root/src/workloads/run_falkordb.py"
python "$root/src/workloads/run_arangodb.py"

Write-Host "=== 4. Collecting footprint (docker stats) ===" -ForegroundColor Cyan
python "$root/src/report/collect_footprint.py"

Write-Host "=== 5. Regenerating README results tables + charts ===" -ForegroundColor Cyan
python "$root/src/report/aggregate_results.py"

Write-Host "Done. See README.md and charts/." -ForegroundColor Green
