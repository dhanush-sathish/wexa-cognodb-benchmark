"""
Reads results/*.json (one per platform) and:
  1. writes charts/*.png (matplotlib, no seaborn/styling deps)
  2. regenerates the results tables in README.md between the
     <!-- RESULTS:START --> / <!-- RESULTS:END --> markers

Run this after every platform has been loaded and benchmarked.

Usage:
    python src/report/aggregate_results.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from common import config  # noqa: E402

PLATFORM_ORDER = ["cognodb", "neo4j", "memgraph", "falkordb", "arangodb"]
HOP_CATEGORIES = ["point_lookup", "filtered_lookup", "hop_1", "hop_2", "hop_3", "aggregation"]
README_PATH = config.ROOT / "README.md"
START_MARKER = "<!-- RESULTS:START -->"
END_MARKER = "<!-- RESULTS:END -->"


def load_all_results():
    results = {}
    for platform in PLATFORM_ORDER:
        path = config.RESULTS_DIR / f"{platform}.json"
        if path.exists():
            results[platform] = json.loads(path.read_text(encoding="utf-8"))
    return results


def fmt(v, suffix=""):
    return f"{v}{suffix}" if v is not None else "n/a"


def build_load_table(results):
    lines = ["| Platform | Nodes/sec | Rels/sec | Index creation (s) | Total load time (s) | "
              "Verified count matches source? | Load error | Cleanup error |",
              "|---|---|---|---|---|---|---|---|"]
    for platform in PLATFORM_ORDER:
        load = results.get(platform, {}).get("load", {})
        verified = "n/a"
        vn, ve = load.get("verified_node_count"), load.get("verified_edge_count")
        n, e = load.get("node_count"), load.get("edge_count")
        if vn is not None and ve is not None and n is not None and e is not None:
            verified = "yes" if (vn == n and ve == e) else f"NO ({vn}/{ve} vs {n}/{e})"
        lines.append(f"| {platform} | {fmt(load.get('nodes_per_second'))} | "
                      f"{fmt(load.get('relationships_per_second'))} | {fmt(load.get('index_creation_seconds'))} | "
                      f"{fmt(load.get('total_load_seconds'))} | "
                      f"{verified} | {load.get('error') or 'none'} | {load.get('cleanup_error') or 'none'} |")
    return "\n".join(lines)


def build_cold_start_table(results):
    lines = ["| Platform | Cold-start first query (ms) |", "|---|---|"]
    for platform in PLATFORM_ORDER:
        cs = results.get(platform, {}).get("cold_start_ms")
        if isinstance(cs, dict):
            cell = f"error: {cs.get('error')}"
        else:
            cell = fmt(cs)
        lines.append(f"| {platform} | {cell} |")
    return "\n".join(lines)


def build_workload_table(results):
    lines = ["| Platform | " + " | ".join(f"{c} p50/p95 (ms)" for c in HOP_CATEGORIES) + " |",
              "|---|" + "|".join(["---"] * len(HOP_CATEGORIES)) + "|"]
    for platform in PLATFORM_ORDER:
        workloads = results.get(platform, {}).get("workloads", {})
        cells = []
        for cat in HOP_CATEGORIES:
            w = workloads.get(cat, {})
            if "error" in w:
                cells.append(f"error: {w['error'][:40]}")
            else:
                cells.append(f"{fmt(w.get('p50_ms'))} / {fmt(w.get('p95_ms'))}")
        lines.append(f"| {platform} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_mixed_table(results):
    concurrencies = sorted({int(k) for r in results.values() for k in r.get("mixed_workload", {})})
    if not concurrencies:
        return "_No mixed-workload data yet._"
    lines = ["| Platform | " + " | ".join(f"{c} clients (ops/sec)" for c in concurrencies) + " |",
              "|---|" + "|".join(["---"] * len(concurrencies)) + "|"]
    for platform in PLATFORM_ORDER:
        mixed = results.get(platform, {}).get("mixed_workload", {})
        cells = []
        for c in concurrencies:
            level = mixed.get(str(c), {})
            if "error" in level:
                cells.append(f"error: {level['error'][:30]}")
            else:
                cells.append(fmt(level.get("ops_per_second")))
        lines.append(f"| {platform} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_footprint_table(results):
    lines = ["| Platform | Footprint |", "|---|---|"]
    for platform in PLATFORM_ORDER:
        fp = results.get(platform, {}).get("footprint", {})
        cell = fp.get("note") or fp.get("mem_usage") or ("not yet collected" if not fp else json.dumps(fp))
        lines.append(f"| {platform} | {cell} |")
    return "\n".join(lines)


def build_index_table(results):
    lines = ["| Platform | unique id index | dept index |", "|---|---|---|"]
    for platform in PLATFORM_ORDER:
        idx = results.get(platform, {}).get("indexes_created", {})
        lines.append(f"| {platform} | {idx.get('unique_id') or 'none'} | {idx.get('dept_index') or 'none'} |")
    return "\n".join(lines)


def make_charts(results):
    config.CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    # p95 latency per hop depth, grouped by platform
    fig, ax = plt.subplots(figsize=(9, 5))
    hop_cats = ["hop_1", "hop_2", "hop_3"]
    width = 0.15
    x = range(len(hop_cats))
    for i, platform in enumerate(PLATFORM_ORDER):
        workloads = results.get(platform, {}).get("workloads", {})
        vals = [workloads.get(c, {}).get("p95_ms") or 0 for c in hop_cats]
        ax.bar([xi + i * width for xi in x], vals, width=width, label=platform)
    ax.set_xticks([xi + width * (len(PLATFORM_ORDER) - 1) / 2 for xi in x])
    ax.set_xticklabels(["1-hop", "2-hop", "3-hop"])
    ax.set_ylabel("p95 latency (ms)")
    ax.set_title("Traversal latency (p95) by hop depth")
    ax.legend()
    fig.tight_layout()
    fig.savefig(config.CHARTS_DIR / "traversal_p95.png", dpi=150)
    plt.close(fig)

    # mixed workload throughput vs concurrency
    fig, ax = plt.subplots(figsize=(9, 5))
    concurrencies = sorted({int(k) for r in results.values() for k in r.get("mixed_workload", {})})
    for platform in PLATFORM_ORDER:
        mixed = results.get(platform, {}).get("mixed_workload", {})
        vals = [mixed.get(str(c), {}).get("ops_per_second") for c in concurrencies]
        if any(v is not None for v in vals):
            ax.plot(concurrencies, [v or 0 for v in vals], marker="o", label=platform)
    ax.set_xlabel("Concurrent clients")
    ax.set_ylabel("Sustained ops/sec")
    ax.set_title("Mixed read/write throughput vs. concurrency")
    ax.legend()
    fig.tight_layout()
    fig.savefig(config.CHARTS_DIR / "mixed_workload_throughput.png", dpi=150)
    plt.close(fig)


def inject_into_readme(section_md):
    text = README_PATH.read_text(encoding="utf-8")
    if START_MARKER not in text or END_MARKER not in text:
        print("WARNING: README.md is missing the RESULTS markers; skipping injection.")
        return
    before = text.split(START_MARKER)[0]
    after = text.split(END_MARKER)[1]
    new_text = before + START_MARKER + "\n" + section_md + "\n" + END_MARKER + after
    README_PATH.write_text(new_text, encoding="utf-8")


def main():
    results = load_all_results()
    if not results:
        print("No results found in results/*.json yet -- run the loaders and workloads first.")
        return

    make_charts(results)

    section = "\n".join([
        "### Data loading",
        "", build_load_table(results), "",
        "### Indexes actually created", "", build_index_table(results), "",
        "### Cold start (first query after connecting, before warm-up; "
        "see Caveats for cross-platform measurement differences)",
        "", build_cold_start_table(results), "",
        "### Traversals, lookups & aggregation (p50 / p95, ms; warmed-up)", "", build_workload_table(results), "",
        "![traversal p95](charts/traversal_p95.png)", "",
        "### Mixed read/write workload", "", build_mixed_table(results), "",
        "![mixed workload throughput](charts/mixed_workload_throughput.png)", "",
        "### Footprint", "", build_footprint_table(results), "",
    ])
    inject_into_readme(section)
    print("Charts written to charts/. README.md results section regenerated.")


if __name__ == "__main__":
    main()
