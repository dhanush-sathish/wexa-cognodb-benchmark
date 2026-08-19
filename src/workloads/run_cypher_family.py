"""
Workload runner shared by CognoDB, Neo4j and Memgraph (Bolt + Cypher via the
official `neo4j` driver).

Usage:
    python src/workloads/run_cypher_family.py --platform cognodb
    python src/workloads/run_cypher_family.py --platform neo4j --concurrency 1 10 40
"""
import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from neo4j import GraphDatabase  # noqa: E402

from common import config, queries, stats  # noqa: E402
from common.dataset_meta import DEPARTMENTS  # noqa: E402

WARMUP_ITERATIONS = 20
MEASURED_ITERATIONS = 100
MIXED_WORKLOAD_DURATION_S = 20
MIXED_WORKLOAD_WRITE_RATIO = 0.10  # 10% writes, 90% reads


def run_query_n_times(session, cypher, param_fn, n):
    timer = stats.Timer()
    for _ in range(n):
        params = param_fn()
        with timer.measure():
            session.run(cypher, **params).consume()
    return timer.percentiles()


def bench_category(session, name, cypher, param_fn):
    for _ in range(WARMUP_ITERATIONS):
        session.run(cypher, **param_fn()).consume()
    return {name: run_query_n_times(session, cypher, param_fn, MEASURED_ITERATIONS)}


def mixed_workload_worker(driver, start_nodes, node_ids, duration_s, write_ratio, seq_counter, lock, stop_at):
    ops = 0
    rng = random.Random()
    with driver.session() as session:
        while time.perf_counter() < stop_at:
            if rng.random() < write_ratio:
                with lock:
                    seq_counter[0] += 1
                    seq = seq_counter[0]
                src, dst = rng.choice(node_ids), rng.choice(node_ids)
                session.run(queries.CYPHER_WRITE_EDGE, src=src, dst=dst, seq=seq).consume()
            else:
                node_id = rng.choice(start_nodes)
                session.run(queries.CYPHER_HOP_1, id=node_id).consume()
            ops += 1
    return ops


def run_mixed_workload(target, start_nodes, node_ids, concurrency_levels):
    results = {}
    for concurrency in concurrency_levels:
        seq_counter = [0]
        lock = threading.Lock()
        drivers = [GraphDatabase.driver(target.uri, auth=(target.user, target.password))
                   for _ in range(concurrency)]
        stop_at = time.perf_counter() + MIXED_WORKLOAD_DURATION_S
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(mixed_workload_worker, drivers[i], start_nodes, node_ids,
                                    MIXED_WORKLOAD_DURATION_S, MIXED_WORKLOAD_WRITE_RATIO,
                                    seq_counter, lock, stop_at)
                       for i in range(concurrency)]
            total_ops = sum(f.result() for f in futures)
        elapsed = time.perf_counter() - t0
        for d in drivers:
            d.close()
        results[str(concurrency)] = {
            "concurrency": concurrency,
            "duration_seconds": round(elapsed, 2),
            "total_ops": total_ops,
            "ops_per_second": round(total_ops / elapsed, 1),
            "write_ratio": MIXED_WORKLOAD_WRITE_RATIO,
        }
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", required=True, choices=list(config.BOLT_TARGETS))
    parser.add_argument("--concurrency", nargs="+", type=int, default=[1, 10, 40])
    parser.add_argument("--skip-mixed", action="store_true")
    args = parser.parse_args()

    target = config.BOLT_TARGETS[args.platform]()
    start_nodes = json.loads((config.PROCESSED_DIR / "sample_start_nodes.json").read_text())

    with open(config.PROCESSED_DIR / "nodes.csv", encoding="utf-8") as f:
        import csv
        all_ids = [int(r["id"]) for r in csv.DictReader(f)]

    driver = GraphDatabase.driver(target.uri, auth=(target.user, target.password))
    driver.verify_connectivity()

    rng = random.Random(1)
    category_results = {}
    with driver.session() as session:
        category_results.update(bench_category(
            session, "point_lookup", queries.CYPHER_POINT_LOOKUP,
            lambda: {"id": rng.choice(start_nodes)}))
        category_results.update(bench_category(
            session, "filtered_lookup", queries.CYPHER_FILTERED_LOOKUP,
            lambda: {"dept": rng.choice(DEPARTMENTS)}))
        category_results.update(bench_category(
            session, "hop_1", queries.CYPHER_HOP_1,
            lambda: {"id": rng.choice(start_nodes)}))
        category_results.update(bench_category(
            session, "hop_2", queries.CYPHER_HOP_2,
            lambda: {"id": rng.choice(start_nodes)}))
        category_results.update(bench_category(
            session, "hop_3", queries.CYPHER_HOP_3,
            lambda: {"id": rng.choice(start_nodes)}))
        category_results.update(bench_category(
            session, "aggregation", queries.CYPHER_AGGREGATION, lambda: {}))

    mixed = {} if args.skip_mixed else run_mixed_workload(target, start_nodes, all_ids, args.concurrency)
    driver.close()

    result = {"workloads": category_results, "mixed_workload": mixed}
    path = stats.write_result(config.RESULTS_DIR, args.platform, result)
    print(f"Wrote {path}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
