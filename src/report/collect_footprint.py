"""
Records the "Footprint" metric (section 5.2) for every platform.

For the self-hosted Docker platforms we can read live container stats
(memory usage, CPU%) directly from the Docker Engine API via `docker stats`.
For CognoDB (a managed free-tier service) none of that is exposed to the
client -- we record "not observable" rather than guessing, per the
assignment's own instruction in section 5.2.

Usage:
    python src/report/collect_footprint.py
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from common import config, stats  # noqa: E402

CONTAINER_NAMES = {
    "neo4j": "cognodb-bench-neo4j",
    "memgraph": "cognodb-bench-memgraph",
    "falkordb": "cognodb-bench-falkordb",
    "arangodb": "cognodb-bench-arangodb",
}


def docker_stats(container_name):
    try:
        out = subprocess.check_output(
            ["docker", "stats", "--no-stream", "--format",
             '{"mem_usage":"{{.MemUsage}}","mem_percent":"{{.MemPerc}}","cpu_percent":"{{.CPUPerc}}"}',
             container_name],
            text=True, timeout=15,
        )
        return json.loads(out.strip())
    except Exception as e:
        return {"error": str(e)}


def main():
    for platform, container in CONTAINER_NAMES.items():
        footprint = docker_stats(container)
        stats.write_result(config.RESULTS_DIR, platform, {"footprint": footprint})
        print(platform, footprint)

    stats.write_result(config.RESULTS_DIR, "cognodb", {
        "footprint": {
            "note": "not observable -- CognoDB's managed free tier does not expose memory/CPU/storage "
                    "metrics to the client driver or a public metrics API. Documented per the assignment's "
                    "own allowance in section 5.2 rather than estimated.",
        }
    })
    print("cognodb: not observable (see note in results/cognodb.json)")


if __name__ == "__main__":
    main()
