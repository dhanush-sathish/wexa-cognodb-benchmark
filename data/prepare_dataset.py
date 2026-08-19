"""
Turns the raw email-Enron edge list into:
  data/processed/nodes.csv             id,email_hash,dept
  data/processed/edges.csv             src,dst
  data/processed/sample_start_nodes.json   200 node ids, seeded -- IDENTICAL
                                            across every platform run, so hop
                                            traversals and lookups start from
                                            exactly the same nodes everywhere.
  data/processed/dataset_stats.json    node/edge counts for the README

The dataset itself (email-Enron) carries no real names or addresses -- SNAP
publishes it pre-anonymized as integer node IDs. We add synthetic `email_hash`
and `dept` properties (deterministic, seeded) purely so the benchmark has
something to filter/index on for the "indexed/filtered lookup" and
"aggregation" metrics -- they do not represent real people.
"""
import csv
import hashlib
import json
import random
import sys
from pathlib import Path

from download_dataset import download

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common.dataset_meta import DEPARTMENTS  # noqa: E402

PROCESSED_DIR = Path(__file__).parent / "processed"
SEED = 20260819  # fixed so every platform sees the identical derived data


def synthetic_email_hash(node_id: int) -> str:
    return hashlib.sha1(f"enron-node-{node_id}".encode()).hexdigest()[:12]


def build():
    txt_path = download()
    rng = random.Random(SEED)

    node_ids = set()
    edges = []
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            src, dst = line.split()
            src, dst = int(src), int(dst)
            node_ids.add(src)
            node_ids.add(dst)
            edges.append((src, dst))

    node_ids = sorted(node_ids)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    with open(PROCESSED_DIR / "nodes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "email_hash", "dept"])
        for nid in node_ids:
            w.writerow([nid, synthetic_email_hash(nid), rng.choice(DEPARTMENTS)])

    with open(PROCESSED_DIR / "edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["src", "dst"])
        for src, dst in edges:
            w.writerow([src, dst])

    # Deterministic sample of start nodes shared by every platform's workload run.
    sample_size = min(200, len(node_ids))
    start_nodes = rng.sample(node_ids, sample_size)
    with open(PROCESSED_DIR / "sample_start_nodes.json", "w", encoding="utf-8") as f:
        json.dump(start_nodes, f)

    stats = {
        "source": "SNAP email-Enron (https://snap.stanford.edu/data/email-Enron.html)",
        "node_count": len(node_ids),
        "edge_count": len(edges),
        "seed": SEED,
        "sample_start_node_count": sample_size,
    }
    with open(PROCESSED_DIR / "dataset_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    build()
