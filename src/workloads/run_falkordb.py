"""
Workload runner for FalkorDB (Cypher over RESP).

Usage:
    python src/workloads/run_falkordb.py
"""
import csv
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from falkordb import FalkorDB  # noqa: E402

from common import config, queries, stats  # noqa: E402
from common.dataset_meta import DEPARTMENTS  # noqa: E402

WARMUP_ITERATIONS = 20
MEASURED_ITERATIONS = 100
MIXED_WORKLOAD_DURATION_S = 20
MIXED_WORKLOAD_WRITE_RATIO = 0.10


def run_query_n_times(g, cypher, param_fn, n):
    timer = stats.Timer()
    for _ in range(n):
        params = param_fn()
        with timer.measure():
            g.query(cypher, params=params)
    return timer.percentiles()


def bench_category(g, name, cypher, param_fn):
    for _ in range(WARMUP_ITERATIONS):
        g.query(cypher, params=param_fn())
    return {name: run_query_n_times(g, cypher, param_fn, MEASURED_ITERATIONS)}


def mixed_workload_worker(cfg, start_nodes, node_ids, write_ratio, seq_counter, lock, stop_at):
    ops = 0
    rng = random.Random()
    db = FalkorDB(host=cfg["host"], port=cfg["port"])
    g = db.select_graph(cfg["graph"])
    while time.perf_counter() < stop_at:
        if rng.random() < write_ratio:
            with lock:
                seq_counter[0] += 1
                seq = seq_counter[0]
            src, dst = rng.choice(node_ids), rng.choice(node_ids)
            g.query(queries.CYPHER_WRITE_EDGE, params={"src": src, "dst": dst, "seq": seq})
        else:
            node_id = rng.choice(start_nodes)
            g.query(queries.CYPHER_HOP_1, params={"id": node_id})
        ops += 1
    return ops


def run_mixed_workload(cfg, start_nodes, node_ids, concurrency_levels):
    results = {}
    for concurrency in concurrency_levels:
        try:
            seq_counter = [0]
            lock = threading.Lock()
            stop_at = time.perf_counter() + MIXED_WORKLOAD_DURATION_S
            t0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                futures = [pool.submit(mixed_workload_worker, cfg, start_nodes, node_ids,
                                        MIXED_WORKLOAD_WRITE_RATIO, seq_counter, lock, stop_at)
                           for _ in range(concurrency)]
                total_ops = sum(f.result() for f in futures)
            elapsed = time.perf_counter() - t0
            results[str(concurrency)] = {
                "concurrency": concurrency,
                "duration_seconds": round(elapsed, 2),
                "total_ops": total_ops,
                "ops_per_second": round(total_ops / elapsed, 1),
                "write_ratio": MIXED_WORKLOAD_WRITE_RATIO,
            }
        except Exception as e:
            results[str(concurrency)] = {"concurrency": concurrency, "error": str(e)}
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", nargs="+", type=int, default=[1, 10, 40])
    parser.add_argument("--skip-mixed", action="store_true")
    args = parser.parse_args()

    cfg = config.falkordb_config()
    start_nodes = json.loads((config.PROCESSED_DIR / "sample_start_nodes.json").read_text())
    with open(config.PROCESSED_DIR / "nodes.csv", encoding="utf-8") as f:
        all_ids = [int(r["id"]) for r in csv.DictReader(f)]

    db = FalkorDB(host=cfg["host"], port=cfg["port"])
    g = db.select_graph(cfg["graph"])

    rng = random.Random(1)
    try:
        cold_id = rng.choice(start_nodes)
        t0 = time.perf_counter()
        g.query(queries.CYPHER_POINT_LOOKUP, params={"id": cold_id})
        cold_start_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    except Exception as e:
        cold_start_ms = {"error": str(e)}

    category_results = {}
    category_results.update(stats.safe("point_lookup", lambda: bench_category(
        g, "point_lookup", queries.CYPHER_POINT_LOOKUP, lambda: {"id": rng.choice(start_nodes)})))
    category_results.update(stats.safe("filtered_lookup", lambda: bench_category(
        g, "filtered_lookup", queries.CYPHER_FILTERED_LOOKUP, lambda: {"dept": rng.choice(DEPARTMENTS)})))
    category_results.update(stats.safe("hop_1", lambda: bench_category(
        g, "hop_1", queries.CYPHER_HOP_1, lambda: {"id": rng.choice(start_nodes)})))
    category_results.update(stats.safe("hop_2", lambda: bench_category(
        g, "hop_2", queries.CYPHER_HOP_2, lambda: {"id": rng.choice(start_nodes)})))
    category_results.update(stats.safe("hop_3", lambda: bench_category(
        g, "hop_3", queries.CYPHER_HOP_3, lambda: {"id": rng.choice(start_nodes)})))
    category_results.update(stats.safe("aggregation", lambda: bench_category(
        g, "aggregation", queries.CYPHER_AGGREGATION, lambda: {})))

    if args.skip_mixed:
        mixed = {}
    else:
        try:
            mixed = run_mixed_workload(cfg, start_nodes, all_ids, args.concurrency)
        except Exception as e:
            mixed = {"error": str(e)}

    result = {"workloads": category_results, "mixed_workload": mixed, "cold_start_ms": cold_start_ms}
    path = stats.write_result(config.RESULTS_DIR, "falkordb", result)
    print(f"Wrote {path}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
