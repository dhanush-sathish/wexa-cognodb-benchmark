# Orchestrates the full benchmark: dataset prep -> load every platform ->
# run every workload -> collect footprint -> regenerate README results tables.
#
# Prerequisites:
#   1. python -m venv .venv ; .venv\Scripts\Activate.ps1 ; pip install -r requirements.txt
#   2. Copy .env.example to .env and fill in COGNODB_URI / COGNODB_PASSWORD
#      (from your own CognoDB Cloud signup -- see README.md section "Setup").
#   3. docker compose up -d   (starts neo4j, memgraph, falkordb, arangodb,
#      each capped to the same 0.5 vCPU / 512MB as CognoDB's free tier)
#   4. (recommended) python scripts/check_connections.py -- confirms all 5
#      platforms are reachable before committing to a full run.
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts/run_all.ps1
#
# Deliberately does NOT set $ErrorActionPreference = "Stop": one platform
# failing (free-tier throttling, a dropped connection, a timeout) must not
# abort benchmarking of the other four -- each Python step below already
# catches its own errors and records them in results/<platform>.json rather
# than crashing, so this script's job is just to keep going and report which
# steps failed at the end.

$root = Split-Path -Parent $PSScriptRoot
$failedSteps = @()

function Invoke-Step {
    param([string]$Label, [string]$ScriptPath, [string[]]$ExtraArgs = @())
    Write-Host "--- $Label ---" -ForegroundColor DarkCyan
    python $ScriptPath @ExtraArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "!!! FAILED: $Label (exit $LASTEXITCODE) -- continuing with remaining platforms" -ForegroundColor Yellow
        $script:failedSteps += $Label
    }
}

Write-Host "=== 1. Preparing dataset ===" -ForegroundColor Cyan
python "$root/data/prepare_dataset.py"

Write-Host "=== 2. Loading data into every platform ===" -ForegroundColor Cyan
Invoke-Step "load cognodb"  "$root/src/loaders/load_cypher_family.py" @("--platform", "cognodb")
Invoke-Step "load neo4j"    "$root/src/loaders/load_cypher_family.py" @("--platform", "neo4j")
Invoke-Step "load memgraph" "$root/src/loaders/load_cypher_family.py" @("--platform", "memgraph")
Invoke-Step "load falkordb" "$root/src/loaders/load_falkordb.py"
Invoke-Step "load arangodb" "$root/src/loaders/load_arangodb.py"

Write-Host "=== 3. Running workloads on every platform ===" -ForegroundColor Cyan
Invoke-Step "workload cognodb"  "$root/src/workloads/run_cypher_family.py" @("--platform", "cognodb")
Invoke-Step "workload neo4j"    "$root/src/workloads/run_cypher_family.py" @("--platform", "neo4j")
Invoke-Step "workload memgraph" "$root/src/workloads/run_cypher_family.py" @("--platform", "memgraph")
Invoke-Step "workload falkordb" "$root/src/workloads/run_falkordb.py"
Invoke-Step "workload arangodb" "$root/src/workloads/run_arangodb.py"

Write-Host "=== 4. Collecting footprint (docker stats) ===" -ForegroundColor Cyan
Invoke-Step "footprint" "$root/src/report/collect_footprint.py"

Write-Host "=== 5. Regenerating README results tables + charts ===" -ForegroundColor Cyan
Invoke-Step "aggregate" "$root/src/report/aggregate_results.py"

if ($failedSteps.Count -gt 0) {
    Write-Host ""
    Write-Host "Done, but $($failedSteps.Count) step(s) failed -- check results/*.json for recorded error fields:" -ForegroundColor Yellow
    $failedSteps | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
} else {
    Write-Host "Done. See README.md and charts/." -ForegroundColor Green
}
