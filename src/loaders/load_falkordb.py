"""
Data loader for FalkorDB. FalkorDB speaks Cypher too (over RESP, not Bolt), so
the query strings are the same as the Neo4j-family loader, but the client
library and connection model differ, hence a separate script.

Usage:
    python src/loaders/load_falkordb.py
"""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from falkordb import FalkorDB  # noqa: E402

from common import config, stats  # noqa: E402

BATCH_SIZE = 1000

INDEX_CANDIDATES = {
    "unique_id": [
        "CREATE INDEX FOR (p:Person) ON (p.id)",
        "CREATE INDEX ON :Person(id)",
    ],
    "dept_index": [
        "CREATE INDEX FOR (p:Person) ON (p.dept)",
        "CREATE INDEX ON :Person(dept)",
    ],
}


def create_indexes(g):
    created = {}
    for name, candidates in INDEX_CANDIDATES.items():
        created[name] = None
        for stmt in candidates:
            try:
                g.query(stmt)
                created[name] = stmt
                break
            except Exception:
                continue
    return created


def main():
    cfg = config.falkordb_config()

    with open(config.PROCESSED_DIR / "nodes.csv", encoding="utf-8") as f:
        nodes = [{"id": int(r["id"]), "email_hash": r["email_hash"], "dept": r["dept"]}
                  for r in csv.DictReader(f)]
    with open(config.PROCESSED_DIR / "edges.csv", encoding="utf-8") as f:
        edges = [{"src": int(r["src"]), "dst": int(r["dst"])} for r in csv.DictReader(f)]

    db = FalkorDB(host=cfg["host"], port=cfg["port"])
    g = db.select_graph(cfg["graph"])

    try:
        g.query("MATCH (n:Person) DETACH DELETE n")
    except Exception:
        pass

    t0 = time.perf_counter()
    for i in range(0, len(nodes), BATCH_SIZE):
        batch = nodes[i:i + BATCH_SIZE]
        g.query(
            "UNWIND $rows AS row CREATE (:Person {id: row.id, email_hash: row.email_hash, dept: row.dept})",
            params={"rows": batch},
        )
    t_nodes = time.perf_counter()

    for i in range(0, len(edges), BATCH_SIZE):
        batch = edges[i:i + BATCH_SIZE]
        g.query(
            "UNWIND $rows AS row MATCH (a:Person {id: row.src}), (b:Person {id: row.dst}) "
            "CREATE (a)-[:EMAILED]->(b)",
            params={"rows": batch},
        )
    t_edges = time.perf_counter()

    indexes = create_indexes(g)

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
    path = stats.write_result(config.RESULTS_DIR, "falkordb", result)
    print(f"Wrote {path}")
    print(result)


if __name__ == "__main__":
    main()
