#!/usr/bin/env bash
# Orchestrates the full benchmark: dataset prep -> load every platform ->
# run every workload -> collect footprint -> regenerate README results tables.
#
# Prerequisites:
#   1. python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
#   2. Copy .env.example to .env and fill in COGNODB_URI / COGNODB_PASSWORD.
#   3. docker compose up -d
#   4. (recommended) python scripts/check_connections.py -- confirms all 5
#      platforms are reachable before committing to a full run.
#
# Deliberately NOT using `set -e`: one platform failing (free-tier throttling,
# a dropped connection, a timeout) must not abort benchmarking of the other
# four -- each Python step below already catches its own errors and records
# them in results/<platform>.json rather than crashing, so this script's job
# is just to keep going and summarize what failed at the end.
set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed_steps=()

run_step() {
  echo "--- $1 ---"
  shift
  if ! "$@"; then
    echo "!!! FAILED: $* (continuing with remaining platforms)"
    failed_steps+=("$*")
  fi
}

echo "=== 1. Preparing dataset ==="
python "$root/data/prepare_dataset.py"

echo "=== 2. Loading data into every platform ==="
run_step "load cognodb"  python "$root/src/loaders/load_cypher_family.py" --platform cognodb
run_step "load neo4j"    python "$root/src/loaders/load_cypher_family.py" --platform neo4j
run_step "load memgraph" python "$root/src/loaders/load_cypher_family.py" --platform memgraph
run_step "load falkordb" python "$root/src/loaders/load_falkordb.py"
run_step "load arangodb" python "$root/src/loaders/load_arangodb.py"

echo "=== 3. Running workloads on every platform ==="
run_step "workload cognodb"  python "$root/src/workloads/run_cypher_family.py" --platform cognodb
run_step "workload neo4j"    python "$root/src/workloads/run_cypher_family.py" --platform neo4j
run_step "workload memgraph" python "$root/src/workloads/run_cypher_family.py" --platform memgraph
run_step "workload falkordb" python "$root/src/workloads/run_falkordb.py"
run_step "workload arangodb" python "$root/src/workloads/run_arangodb.py"

echo "=== 4. Collecting footprint (docker stats) ==="
run_step "footprint" python "$root/src/report/collect_footprint.py"

echo "=== 5. Regenerating README results tables + charts ==="
run_step "aggregate" python "$root/src/report/aggregate_results.py"

if [ ${#failed_steps[@]} -gt 0 ]; then
  echo ""
  echo "Done, but ${#failed_steps[@]} step(s) failed -- check results/*.json for recorded error fields:"
  printf '  - %s\n' "${failed_steps[@]}"
else
  echo "Done. See README.md and charts/."
fi
