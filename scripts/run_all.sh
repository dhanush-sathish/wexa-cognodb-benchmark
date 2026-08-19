#!/usr/bin/env bash
# Orchestrates the full benchmark: dataset prep -> load every platform ->
# run every workload -> collect footprint -> regenerate README results tables.
#
# Prerequisites:
#   1. python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
#   2. Copy .env.example to .env and fill in COGNODB_URI / COGNODB_PASSWORD.
#   3. docker compose up -d
#
# Usage: bash scripts/run_all.sh
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== 1. Preparing dataset ==="
python "$root/data/prepare_dataset.py"

echo "=== 2. Loading data into every platform ==="
python "$root/src/loaders/load_cypher_family.py" --platform cognodb
python "$root/src/loaders/load_cypher_family.py" --platform neo4j
python "$root/src/loaders/load_cypher_family.py" --platform memgraph
python "$root/src/loaders/load_falkordb.py"
python "$root/src/loaders/load_arangodb.py"

echo "=== 3. Running workloads on every platform ==="
python "$root/src/workloads/run_cypher_family.py" --platform cognodb
python "$root/src/workloads/run_cypher_family.py" --platform neo4j
python "$root/src/workloads/run_cypher_family.py" --platform memgraph
python "$root/src/workloads/run_falkordb.py"
python "$root/src/workloads/run_arangodb.py"

echo "=== 4. Collecting footprint (docker stats) ==="
python "$root/src/report/collect_footprint.py"

echo "=== 5. Regenerating README results tables + charts ==="
python "$root/src/report/aggregate_results.py"

echo "Done. See README.md and charts/."
