"""
Data loader shared by CognoDB, Neo4j and Memgraph -- all three speak Cypher
over Bolt through the official `neo4j` Python driver, so one script handles
all three (point it at a different platform with --platform).

Usage:
    python src/loaders/load_cypher_family.py --platform cognodb
    python src/loaders/load_cypher_family.py --platform neo4j
    python src/loaders/load_cypher_family.py --platform memgraph
"""
import argparse
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from neo4j import GraphDatabase  # noqa: E402

from common import config, stats  # noqa: E402

BATCH_SIZE = 1000

# Each platform may accept a different index/constraint dialect. We try each
# candidate statement in order and record which one (if any) worked, instead
# of assuming one dialect and silently running unindexed.
INDEX_CANDIDATES = {
    "unique_id": [
        "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT ON (p:Person) ASSERT p.id IS UNIQUE",
        "CREATE INDEX ON :Person(id)",
    ],
    "dept_index": [
        "CREATE INDEX person_dept IF NOT EXISTS FOR (p:Person) ON (p.dept)",
        "CREATE INDEX ON :Person(dept)",
    ],
}


def create_indexes(session):
    created = {}
    for name, candidates in INDEX_CANDIDATES.items():
        created[name] = None
        for stmt in candidates:
            try:
                session.run(stmt).consume()
                created[name] = stmt
                break
            except Exception:
                continue
    return created


def load_nodes(session, rows):
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        session.run(
            "UNWIND $rows AS row CREATE (:Person {id: row.id, email_hash: row.email_hash, dept: row.dept})",
            rows=batch,
        ).consume()


def load_edges(session, rows):
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        session.run(
            "UNWIND $rows AS row MATCH (a:Person {id: row.src}), (b:Person {id: row.dst}) "
            "CREATE (a)-[:EMAILED]->(b)",
            rows=batch,
        ).consume()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", required=True, choices=list(config.BOLT_TARGETS))
    args = parser.parse_args()

    target = config.BOLT_TARGETS[args.platform]()

    with open(config.PROCESSED_DIR / "nodes.csv", encoding="utf-8") as f:
        nodes = [{"id": int(r["id"]), "email_hash": r["email_hash"], "dept": r["dept"]}
                  for r in csv.DictReader(f)]
    with open(config.PROCESSED_DIR / "edges.csv", encoding="utf-8") as f:
        edges = [{"src": int(r["src"]), "dst": int(r["dst"])} for r in csv.DictReader(f)]

    driver = GraphDatabase.driver(target.uri, auth=(target.user, target.password))
    driver.verify_connectivity()

    with driver.session() as session:
        try:
            session.run("MATCH (n:Person) DETACH DELETE n").consume()
        except Exception:
            pass

        t0 = time.perf_counter()
        load_nodes(session, nodes)
        t_nodes = time.perf_counter()
        load_edges(session, edges)
        t_edges = time.perf_counter()

        indexes = create_indexes(session)

    driver.close()

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
    path = stats.write_result(config.RESULTS_DIR, args.platform, result)
    print(f"Wrote {path}")
    print(result)


if __name__ == "__main__":
    main()
