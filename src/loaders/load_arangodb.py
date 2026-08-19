"""
Data loader for ArangoDB. ArangoDB is the deliberate multi-model/AQL outlier in
this benchmark (see src/common/queries.py) -- everything else speaks Cypher.

Usage:
    python src/loaders/load_arangodb.py
"""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from arango import ArangoClient  # noqa: E402

from common import config, stats  # noqa: E402

BATCH_SIZE = 1000


def main():
    cfg = config.arangodb_config()
    client = ArangoClient(hosts=cfg["url"])

    sys_db = client.db("_system", username=cfg["user"], password=cfg["password"])
    if not sys_db.has_database(cfg["db"]):
        sys_db.create_database(cfg["db"])
    db = client.db(cfg["db"], username=cfg["user"], password=cfg["password"])

    if db.has_collection("emailed"):
        db.delete_collection("emailed")
    if db.has_collection("persons"):
        db.delete_collection("persons")
    persons = db.create_collection("persons")
    emailed = db.create_collection("emailed", edge=True)

    with open(config.PROCESSED_DIR / "nodes.csv", encoding="utf-8") as f:
        nodes = [{"_key": r["id"], "id": int(r["id"]), "email_hash": r["email_hash"], "dept": r["dept"]}
                  for r in csv.DictReader(f)]
    with open(config.PROCESSED_DIR / "edges.csv", encoding="utf-8") as f:
        edges = [{"_from": f"persons/{r['src']}", "_to": f"persons/{r['dst']}"}
                  for r in csv.DictReader(f)]

    t0 = time.perf_counter()
    for i in range(0, len(nodes), BATCH_SIZE):
        persons.insert_many(nodes[i:i + BATCH_SIZE], overwrite_mode="ignore")
    t_nodes = time.perf_counter()

    for i in range(0, len(edges), BATCH_SIZE):
        emailed.insert_many(edges[i:i + BATCH_SIZE], overwrite_mode="ignore")
    t_edges = time.perf_counter()

    indexes = {}
    try:
        persons.add_persistent_index(fields=["id"], unique=True)
        indexes["unique_id"] = "persistent index on persons.id (unique)"
    except Exception as e:
        indexes["unique_id"] = f"failed: {e}"
    try:
        persons.add_persistent_index(fields=["dept"])
        indexes["dept_index"] = "persistent index on persons.dept"
    except Exception as e:
        indexes["dept_index"] = f"failed: {e}"

    node_load_s = t_nodes - t0
    edge_load_s = t_edges - t_nodes
    total_s = t_edges - t0

    result = {
        "load": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "node_load_seconds": round(node_load_s, 3),
            "edge_load_seconds": round(edge_load_s, 3),
            "total_load_seconds": round(total_s, 3),
            "nodes_per_second": round(len(nodes) / node_load_s, 1) if node_load_s > 0 else None,
            "relationships_per_second": round(len(edges) / edge_load_s, 1) if edge_load_s > 0 else None,
        },
        "indexes_created": indexes,
    }
    path = stats.write_result(config.RESULTS_DIR, "arangodb", result)
    print(f"Wrote {path}")
    print(result)


if __name__ == "__main__":
    main()
