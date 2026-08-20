# CognoDB Cloud vs. Managed/Self-Hosted Graph Databases — A Reproducible Benchmark

> Wexa AI take-home assignment: benchmark CognoDB Cloud against at least four
> other graph database platforms, on the same dataset and workloads, and
> report the results honestly. This repo is the benchmark suite, the raw
> results, and the write-up.

## TL;DR

- **Platforms:** [CognoDB Cloud](#why-these-five-platforms) (managed, free
  tier) vs. **Neo4j**, **Memgraph**, **FalkorDB**, **ArangoDB** (all
  self-hosted via Docker, resource-capped to match CognoDB's free tier).
- **Dataset:** SNAP `email-Enron` — 36,692 nodes / 367,662 directed
  relationships. Identical data, identical queries, identical start-node
  sample on every platform.
- **One command reproduces everything:** `scripts/run_all.ps1` (Windows) or
  `scripts/run_all.sh` (Linux/Mac) — see [Reproducing this benchmark](#reproducing-this-benchmark).
- **Results:** see [Results](#results) below — populated by running the
  harness against your own CognoDB free instance + local Docker containers
  (see [Status of this repo](#status-of-this-repo) for exactly what has and
  hasn't been executed so far).

## Table of contents

1. [Why these five platforms](#why-these-five-platforms)
2. [Fairness: resource parity across every platform](#fairness-resource-parity-across-every-platform)
3. [Dataset](#dataset)
4. [Methodology](#methodology)
5. [Reproducing this benchmark](#reproducing-this-benchmark)
6. [Results](#results)
7. [Analysis](#analysis)
8. [Caveats & honest limitations](#caveats--honest-limitations)
9. [How this repo maps to the evaluation criteria](#how-this-repo-maps-to-the-evaluation-criteria)
10. [Status of this repo](#status-of-this-repo)

## Why these five platforms

CognoDB Cloud speaks **Bolt + Cypher** through the official Neo4j driver
(the assignment's own setup instructions confirm this). To keep the
comparison meaningful rather than arbitrary, the four comparison platforms
were chosen to answer three different questions at once:

| Platform | Why it's here |
|---|---|
| **Neo4j** | The reference implementation of Bolt + Cypher, and the most likely thing CognoDB is positioning itself against directly. If CognoDB is protocol-compatible, this is the closest apples-to-apples comparison possible. |
| **Memgraph** | A second independent Cypher engine (in-memory, C++), so we get more than one data point for "how do different Cypher implementations perform on identical queries," not just CognoDB-vs-Neo4j. |
| **FalkorDB** | Cypher again, but on a completely different storage engine (sparse-matrix/GraphBLAS via Redis), which stress-tests whether the "same query, different engine" comparison holds up on a very different architecture. |
| **ArangoDB** | The deliberate outlier: multi-model, AQL instead of Cypher. Included so the benchmark isn't just "four flavors of Cypher" — it shows what changes (and what doesn't) when the query language itself differs, which is a real switching-cost question for anyone evaluating CognoDB. |

All four are either free-tier/self-hostable at no cost, all have first-class
Python clients, and all are credible, currently-maintained products (not
toy/abandoned projects) — this was itself part of the selection bar.

**Rejected candidates and why:** Amazon Neptune (no meaningful free tier —
would violate the fairness rule outright), TigerGraph Cloud and Azure Cosmos
DB Gremlin API (free tiers exist but are usage-credit-based rather than a
fixed small instance, making resource parity hard to state precisely and
harder for a third party to reproduce for free).

## Fairness: resource parity across every platform

Per the assignment's fairness note, every platform runs on the same
resource envelope as CognoDB's free `c0` instance:

| Platform | vCPU | RAM | Disk | How enforced |
|---|---|---|---|---|
| CognoDB Cloud | burst to 0.5 | 512MB | 1GB (500 IOPS, 200 connections) | Vendor's free "c0" tier, as-is |
| Neo4j | 0.5 | 512MB (heap capped to 256MB + 128MB page cache) | volume, unbounded but dataset is ~50MB | `docker-compose.yml`: `cpus: 0.5`, `mem_limit: 512m` |
| Memgraph | 0.5 | 512MB (`--memory-limit=400`) | same | same |
| FalkorDB | 0.5 | 512MB (`--maxmemory 400mb`) | same | same |
| ArangoDB | 0.5 | 512MB | same | same |

**RAM discrepancy, now resolved:** the assignment PDF's prose says CognoDB's
free tier is "256 MB RAM"; cognodb.com/pricing, fetched directly on
2026-08-20, states "512 MB" (along with "burst to 0.5 vCPU," "1 GB" disk,
"200" connections, "up to 500 IOPS," "no card required"). We're treating the
live pricing page as authoritative since it's the more specific, checkable,
and current source, and capped the four self-hosted platforms to match it
(512MB). If you re-run this later and CognoDB's page has changed, re-check
and update this line — vendor pricing pages are not a fixed target.

**CognoDB instance region:** `us-east4` (N. Virginia) — the only region
offered on the free `c0` tier at signup time (2026-08-20); there was no
region picker to choose a closer location. The benchmark client itself runs
from India. The four self-hosted platforms run in Docker on that same
machine, so they have effectively zero network latency; CognoDB is a real
cross-continent network hop. This is a genuine, unavoidable asymmetry given
the assignment mandates CognoDB Cloud specifically and its free tier is
single-region — documented here rather than hidden, and discussed further in
[Caveats](#caveats--honest-limitations).

## Dataset

[SNAP `email-Enron`](https://snap.stanford.edu/data/email-Enron.html) —
Enron email communication network released by the FERC investigation,
public domain, anonymized to integer node IDs by Stanford.

- **36,692 nodes**, **367,662 directed relationships** (an edge `i -> j`
  means `i` sent at least one email to `j`; SNAP's own page describes the
  graph as undirected with 183,831 edges, but the published edge list
  contains both directions of each communicating pair, so this harness
  keeps the directed representation — arguably more realistic for an email
  graph, and it's what `data/prepare_dataset.py` actually loads).
- Sits inside the assignment's suggested 100k–500k relationship range and
  comfortably fits a 1GB disk / 512MB RAM tier.
- Every node gets two **synthetic** properties, generated deterministically
  from a fixed seed (`20260819`) so every platform sees byte-identical
  data: `email_hash` (a truncated SHA-1 of the node ID — not a real email
  address) and `dept` (one of 10 fixed department names, seeded pseudo-random
  assignment). These exist purely so the benchmark has something to filter
  and group by for the lookup/aggregation metrics — SNAP's raw dataset has
  no such attributes.
- `data/prepare_dataset.py` also writes `sample_start_nodes.json`: 200 node
  IDs sampled once, from the same seed, and reused as the traversal/lookup
  start points on **every** platform — so hop-depth comparisons aren't
  comparing different random walks on different platforms.

Load method: driver-side batched writes (`UNWIND` in 1,000-row batches for
the four Cypher platforms, `insert_many` in 1,000-doc batches for ArangoDB)
— not a bulk-import tool, so ingest numbers reflect realistic
application-level loading, not each vendor's fastest possible bulk loader.
This is a deliberate, stated choice — see [Caveats](#caveats--honest-limitations).

## Methodology

- **Same logical query, per platform's native language.** Cypher queries
  (`src/common/queries.py`) are shared verbatim across CognoDB/Neo4j/
  Memgraph/FalkorDB; AQL translations for ArangoDB express the identical
  logical query (same hop depth, same filter, same aggregation).
- **Cold start:** the first query issued after connecting, before any
  warm-up iterations, is timed separately and reported as `cold_start_ms`.
  Precisely: the driver's connection handshake (`verify_connectivity()`)
  happens first and is *not* included in this number — `cold_start_ms`
  isolates first-query cost (query planning/caching cold, no prior page
  cache warmth) from raw network/TLS handshake cost, rather than bundling
  both under one label. It's still distinct from every category's
  warmed-up p50/p95/p99 below — see the assignment's "what a strong
  submission looks like" note on separating warm vs. cold
  numbers.
- **Warm-up:** 20 untimed iterations per query category before measurement.
- **Measurement:** 100 timed iterations per read workload (exceeds the
  assignment's suggested ≥100 minimum), wall-clock per-call latency
  recorded client-side, p50/p95/p99 reported (not just mean).
- **Mixed workload:** concurrent clients (default sweep: 1 / 10 / 40) each
  running 90% reads (1-hop traversal from a random start node) / 10% writes
  (new relationship insert) for a fixed 20-second window per concurrency
  level; sustained ops/sec reported per level.
- **Same client, same network path:** all runs execute from the same
  machine in the same session, back-to-back, so network/CPU noise is at
  least consistent across platforms within one run (see caveats on
  variance below).
- **Automation:** `scripts/run_all.ps1` / `run_all.sh` run the entire
  pipeline — dataset prep, load, workloads, footprint, report — with zero
  manual steps beyond providing credentials in `.env`.
- **Failure isolation:** every load/query/mixed-workload step is individually
  caught. A single platform timing out, throttling, or dropping a connection
  is recorded as `"error": "..."` in that platform's `results/<platform>.json`
  and the harness moves on — it does not discard already-collected results
  for that platform, and it does not abort benchmarking of the other four.
  This is what makes "record every caveat honestly... timeouts, failed runs"
  (assignment §5.3) actually enforceable rather than aspirational.
- **Load verification:** after loading, each loader re-queries the platform
  for its actual node/relationship count (`verified_node_count` /
  `verified_edge_count` in the results JSON) so "identical dataset on every
  platform" is a checked fact, not just an assumption.

## Reproducing this benchmark

```bash
git clone <this-repo-url>
cd wexa-cognodb-benchmark
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env
# Sign up at https://console.cognodb.com/signup (free, no card), create a
# free c0 instance, and paste its bolt+s:// URI and password into .env.

docker compose up -d   # starts neo4j, memgraph, falkordb, arangodb,
                        # each capped to 0.5 vCPU / 512MB (see docker-compose.yml)

python scripts/check_connections.py   # optional but recommended pre-flight:
                                       # confirms all 5 platforms are reachable
                                       # before committing to a full run

# Windows
powershell -ExecutionPolicy Bypass -File scripts/run_all.ps1
# Linux/Mac
bash scripts/run_all.sh
```

Anyone with a free CognoDB account and Docker installed can run this
end-to-end with no paid resources.

## Results

<!-- RESULTS:START -->
_Not yet generated — run `scripts/run_all.ps1` (or `run_all.sh`) against a
real CognoDB free instance and the Docker Compose stack, then
`python src/report/aggregate_results.py` will replace this section with the
full results matrix and charts. See [Status of this repo](#status-of-this-repo)._
<!-- RESULTS:END -->

## Analysis

_To be filled in after a real run — see [Status of this repo](#status-of-this-repo).
The template below is what this section will cover once results exist; do not
read it as a claim that these are the actual findings._

- **Ingest throughput:** compare nodes/sec and rels/sec across the batched
  `UNWIND`/`insert_many` loaders; call out whether CognoDB's free-tier
  burstable CPU causes ingest to fall off partway through the load (a
  common burstable-tier pattern) versus the fixed-allocation Docker
  containers.
- **Traversal latency vs. hop depth:** whether p95 latency grows linearly,
  worse, or better than linearly with hop depth per platform — this is
  usually the most architecturally revealing number in a graph-DB
  comparison (native graph storage vs. adjacency-list-over-KV vs.
  matrix-multiplication engines like FalkorDB should show different growth
  curves).
- **Lookup latency:** point lookup vs. filtered/indexed lookup gap per
  platform — a big gap implies the index isn't being used the way it is on
  other platforms (see the "indexes actually created" table — index DDL
  silently failing on one platform is a realistic outcome worth catching,
  not hiding).
- **Mixed workload scaling:** which platforms keep scaling ops/sec from 1
  to 10 to 40 clients, and which plateau or regress — plateauing under a
  0.5 vCPU cap is expected and not a knock against any vendor; the point is
  documenting *where* each one plateaus.
- **Root-cause notes:** tie back to each platform's storage model (native
  graph vs. property graph over a KV/relational core vs. GraphBLAS sparse
  matrices) rather than stopping at "X was faster than Y."

## Caveats & honest limitations

- **Loader is driver-batched, not each vendor's bulk-import tool.** Several
  of these platforms have a purpose-built bulk loader (`neo4j-admin
  import`, ArangoDB's `arangoimport`) that would load faster than batched
  `UNWIND`/`insert_many` — but CognoDB's setup instructions only document
  driver access, so batched driver writes is the one loading method
  available on *every* platform, which is what fairness requires here.
  Real bulk-import numbers, where available, would be faster and are not
  reflected below.
- **Free-tier burstable CPU is not a fixed guarantee.** CognoDB's spec is
  explicitly "burstable" 0.5 vCPU; sustained load may throttle below that
  after a burst window. Where observed, this is called out per-platform in
  the results rather than averaged away.
- **CognoDB's actual free-tier RAM is ambiguous (256MB per the assignment
  PDF vs. 512MB per CognoDB's own site)** — see [Fairness](#fairness-resource-parity-across-every-platform).
- **Network path is not identical, and it's a large asymmetry here.** The
  free `c0` tier offered exactly one region at signup — `us-east4` (N.
  Virginia) — with no picker to choose something closer. The benchmark
  client runs from India, so CognoDB's numbers below include a real
  cross-continent round trip (likely tens of ms per query) on top of query
  execution time; the four Docker platforms are localhost with effectively
  zero network latency. This is not a query-engine difference — it's an
  unavoidable consequence of the free tier being single-region and the
  assignment mandating CognoDB Cloud specifically. Read CognoDB's absolute
  latency numbers with this in mind rather than attributing the full gap to
  the database engine itself.
- **Single-run variance is not fully characterized.** The harness reports
  percentiles within a run; it does not yet repeat full runs N times to
  report run-to-run variance. Flagged as a stretch item, not silently
  omitted.
- **Index DDL differs across Cypher dialects.** Neo4j 5 / Memgraph /
  FalkorDB each accept slightly different `CREATE INDEX` syntax; the
  loaders try several candidate statements and record exactly which one
  (if any) succeeded per platform — see the "Indexes actually created"
  table in Results, so a silent unindexed run doesn't get misread as
  "indexed."
- **AQL vs. Cypher is not a pure performance variable.** ArangoDB's numbers
  reflect both the engine *and* a different query formulation; direct
  ArangoDB-vs-Cypher-platform deltas should be read with that in mind.
- **The public `arangodb:3.12` Docker image is Enterprise Edition**, not
  Community — confirmed from its own startup log (`ArangoDB (version
  3.12.10-1 enterprise [linux])`). This wasn't a deliberate choice; it's
  simply what the tag on Docker Hub resolves to. Enterprise may have
  different performance characteristics than the Community edition a real
  free-tier evaluator would run, so ArangoDB's numbers should be read as
  "Enterprise Edition capped to free-tier-equivalent resources," not
  "ArangoDB Community."
- **Edge loads for every Cypher-family platform (CognoDB/Neo4j/Memgraph/
  FalkorDB) create the `Person.id` index/constraint *before* loading edges,
  not after.** Each edge insert does `MATCH (a:Person {id: ...}), (b:Person
  {id: ...})` to find its endpoints; without an index that's a full label
  scan per lookup, twice per edge, across all 367,662 edges. An earlier,
  unindexed-until-the-end version of this loader took Neo4j from an expected
  well-under-a-minute load to 12+ minutes locally, and is almost certainly
  why CognoDB's edge load hit a server-side timeout on its burst-limited CPU
  (see the loaders' `index_creation_seconds` field, reported separately from
  `edge_load_seconds` in the Results load table, for exactly how much time
  each platform's index build itself took).
- **`cold_start_ms` is not measured on a perfectly identical basis across all
  5 platforms.** For CognoDB/Neo4j/Memgraph, the Bolt driver's
  `verify_connectivity()` call completes the TCP/TLS/Bolt handshake *before*
  `cold_start_ms` starts timing, so it isolates first-query cost (cold query
  plan cache, cold page cache) from connection setup. ArangoDB's and
  FalkorDB's clients have no equivalent eager-connect step in this harness,
  so their `cold_start_ms` may also be absorbing some connection-establishment
  cost. Treat cross-platform `cold_start_ms` comparisons involving ArangoDB
  or FalkorDB as directional, not precise — the within-platform warm vs.
  cold contrast is still valid for every platform individually.

## How this repo maps to the evaluation criteria

| Criterion (weight) | Where it's addressed |
|---|---|
| Methodology & fairness (25%) | [Fairness](#fairness-resource-parity-across-every-platform), [Methodology](#methodology), [Caveats](#caveats--honest-limitations) |
| Completeness of metrics (20%) | Every metric in assignment section 5.2 has a corresponding column in [Results](#results) — load throughput, 1/2/3-hop p50/p95, point + filtered lookup p50/p95, aggregation p50/p95, mixed-workload ops/sec per concurrency level, footprint |
| Reproducibility & code quality (20%) | One-command `scripts/run_all.*`, pinned `requirements.txt` and Docker image tags, `src/common` shared across loaders/workloads to avoid duplication |
| README & analysis (15%) | This document + [Analysis](#analysis) |
| Communication (20%) | [ARTICLE.md](ARTICLE.md) — a plain-language write-up of the same methodology and findings for a broader technical audience |

## Status of this repo

Written and verified as of 2026-08-19:

- ✅ Dataset pipeline (`data/download_dataset.py`, `data/prepare_dataset.py`)
  — downloads the real SNAP dataset and generates `nodes.csv` / `edges.csv`
  / `sample_start_nodes.json`. **Actually run**, output: 36,692 nodes /
  367,662 edges.
- ✅ Loaders and workload runners for all 5 platforms — written, code-reviewed
  for consistency, not yet executed end-to-end against live databases.
- ⬜ **Not yet executed:** signing up for CognoDB Cloud, running
  `docker compose up`, and running the full benchmark requires credentials
  and a Docker daemon that only you can provide/run — see
  [Reproducing this benchmark](#reproducing-this-benchmark). Until that
  happens, the [Results](#results) section above is a placeholder, not
  data — do not submit this repo without running it first.
