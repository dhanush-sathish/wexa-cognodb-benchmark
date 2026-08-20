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

    # Delete in bounded batches, same reasoning as load_cypher_family.py's
    # clear_existing(): an unbounded DETACH DELETE over 36,692 nodes /
    # 367,662 relationships can exceed the 512MB cap, and silently
    # swallowing that failure leaves stale data behind that then breaks the
    # next load with a confusing "already exists" error instead of a clear
    # cleanup-failed one.
    cleanup_error = None
    try:
        while True:
            res = g.query("MATCH (n:Person) WITH n LIMIT 10000 DETACH DELETE n RETURN count(n) AS c")
            if not res.result_set or res.result_set[0][0] == 0:
                break
    except Exception as e:
        cleanup_error = str(e)

    load_error = None
    t0 = t_nodes = t_index = t_edges = time.perf_counter()
    try:
        for i in range(0, len(nodes), BATCH_SIZE):
            batch = nodes[i:i + BATCH_SIZE]
            g.query(
                "UNWIND $rows AS row CREATE (:Person {id: row.id, email_hash: row.email_hash, dept: row.dept})",
                params={"rows": batch},
            )
        t_nodes = time.perf_counter()
    except Exception as e:
        load_error = str(e)
        t_nodes = time.perf_counter()

    # Index must exist BEFORE loading edges -- see the matching comment in
    # load_cypher_family.py. Without it, every edge's MATCH (a:Person {id:
    # ...}) is an unindexed full scan across all 36,692 nodes, twice per
    # edge, 367,662 edges -- catastrophically slow instead of a fast lookup.
    try:
        indexes = create_indexes(g)
    except Exception as e:
        indexes = {"error": str(e)}
    t_index = time.perf_counter()

    if load_error is None:
        try:
            for i in range(0, len(edges), BATCH_SIZE):
                batch = edges[i:i + BATCH_SIZE]
                g.query(
                    "UNWIND $rows AS row MATCH (a:Person {id: row.src}), (b:Person {id: row.dst}) "
                    "CREATE (a)-[:EMAILED]->(b)",
                    params={"rows": batch},
                )
            t_edges = time.perf_counter()
        except Exception as e:
            load_error = str(e)
            t_edges = time.perf_counter()
    else:
        t_edges = t_index

    try:
        verified_nodes = g.query("MATCH (n:Person) RETURN count(n) AS c").result_set[0][0]
        verified_edges = g.query("MATCH ()-[r:EMAILED]->() RETURN count(r) AS c").result_set[0][0]
    except Exception:
        verified_nodes = verified_edges = None

    node_load_s = t_nodes - t0
    index_creation_s = t_index - t_nodes
    edge_load_s = t_edges - t_index
    total_s = t_edges - t0

    result = {
        "load": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "verified_node_count": verified_nodes,
            "verified_edge_count": verified_edges,
            "node_load_seconds": round(node_load_s, 3),
            "index_creation_seconds": round(index_creation_s, 3),
            "edge_load_seconds": round(edge_load_s, 3),
            "total_load_seconds": round(total_s, 3),
            "nodes_per_second": round(len(nodes) / node_load_s, 1) if node_load_s > 0 else None,
            "relationships_per_second": round(len(edges) / edge_load_s, 1) if edge_load_s > 0 else None,
            "error": load_error,
            "cleanup_error": cleanup_error,
        },
        "indexes_created": indexes,
    }
    path = stats.write_result(config.RESULTS_DIR, "falkordb", result)
    print(f"Wrote {path}")
    print(result)


if __name__ == "__main__":
    main()
