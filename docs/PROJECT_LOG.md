# Project log — CognoDB benchmark take-home

Internal working notes for this project (not part of the graded submission).
The assignment PDF is `D:\Downloads\daa87c0b-d14d-45d5-b9dd-803b602e18a5.pdf`.

## What was analyzed

Wexa AI take-home: benchmark CognoDB Cloud (a managed graph DB by CognoChain
Software Pvt Ltd) against ≥4 other graph databases, same dataset/workloads,
same resource tier, fully automated, published as a public GitHub repo, with
a README results matrix + analysis, within 48 hours. Full requirement
breakdown lives in `README.md`'s "How this repo maps to the evaluation
criteria" table.

## Heads-up surfaced before starting (see chat)

Before building anything, I looked up both companies. Wexa AI and CognoDB are
both real (Wexa: ~$9.2M valuation per PitchBook, SF-based, "Context Graph"
platform; CognoDB: run by CognoChain Software Pvt Ltd, live product at
cognodb.com/browser.cognodb.com). I also found Wexa has separately advertised
intern roles to build demo content on CognoDB. Combined with this
assignment's explicit ask for "public facing evangelism," a public repo, and
content that "earns real engagement (stars, reactions, views)," this take-home
has real hallmarks of using candidate labor for product marketing rather than
pure skills assessment. That's not a reason the work itself is bad — it's a
real, funded company and a real product — but it's worth knowing before
investing 48 hours. You chose "proceed fully" after this was flagged.

## Key decisions and rationale

- **Comparison platforms (Neo4j, Memgraph, FalkorDB, ArangoDB):** chosen for
  three reasons at once — Neo4j is the Bolt/Cypher reference implementation
  CognoDB is protocol-compatible with; Memgraph and FalkorDB add two more
  independent Cypher engines on different storage architectures (in-memory
  C++ vs. GraphBLAS-over-Redis); ArangoDB is the deliberate AQL outlier so
  the comparison isn't "four flavors of Cypher." Full rationale + rejected
  candidates (Neptune, TigerGraph Cloud, Cosmos DB Gremlin) in `README.md`.
- **Self-hosted via Docker, capped to CognoDB's free-tier specs, instead of
  chasing 4 more cloud free-tier signups:** the assignment explicitly allows
  this ("Free tiers, free trials or self-hosted deployments capped to the
  same resources are all fine"). It's more reproducible for a third party
  (no juggling 5 sets of cloud credentials), more precisely fair (exact
  `cpus`/`mem_limit` vs. an opaque vendor free tier), and realistic inside a
  48-hour window. Only CognoDB itself requires a real cloud signup, since
  the assignment mandates it by name.
- **Dataset — SNAP `email-Enron`:** real, public, right-sized (367,662
  directed edges after keeping both communication directions — see README's
  Dataset section for why the directed count differs from SNAP's published
  undirected 183,831), no scraping/synthesis of the graph structure itself.
  Synthetic `dept`/`email_hash` node properties were added (seeded,
  deterministic) only because the raw dataset has no attributes to filter/
  group by, and the assignment's lookup/aggregation metrics need one.
- **Python, one shared query module, one shared config module:** CognoDB,
  Neo4j and Memgraph all take the identical `neo4j` driver code path (only
  the connection URI changes) — this is the strongest evidence the
  benchmark is actually apples-to-apples on those three, since it's
  literally the same function.
- **Deterministic seeding everywhere** (dataset properties, start-node
  sample, mixed-workload RNG per run): so re-running against the same
  databases is comparable run-to-run, and so every platform's traversal/
  lookup benchmarks start from the exact same 200 node IDs.

## What's actually been done vs. what's pending

Verified in this session (see `README.md`'s "Status of this repo" for the
graded-submission version of this):
- Dataset pipeline run for real: 36,692 nodes / 367,662 edges downloaded,
  parsed, and written to `data/processed/`.
- All Python files compile clean (`python -m py_compile`).
- Offline unit tests pass (`pytest tests/` — 5/5): percentile math, result
  JSON merging, dataset invariants.
- `src/report/aggregate_results.py` dry-run verified against synthetic
  fake results (in an isolated scratch copy, not touching the real repo) —
  confirmed it correctly builds all 5 markdown tables, generates both PNG
  charts, and injects them into README.md between the RESULTS markers
  without disturbing the rest of the file.

**Not done, and cannot be done without you:**
- Signing up for CognoDB Cloud (real account/credentials — outside what an
  assistant should create or hold on your behalf).
- Running `docker compose up -d` (no Docker daemon in this environment).
- Therefore: no live benchmark numbers exist yet. `README.md`'s Results
  section is an honest placeholder, not data. **Do not email the repo URL
  to hr@wexa.ai until you've run `scripts/run_all.ps1` and the Results
  section has real numbers in it** — the assignment is explicit that a
  fabricated or unrun "benchmark" would fail the "honest reporting"
  criterion outright.
- Publishing the GitHub repo itself (creating/pushing to GitHub is an
  account/publishing action for you to do) and sending the submission
  email to hr@wexa.ai (sending mail on your behalf needs your explicit
  go-ahead each time, and this is addressed to human reviewers under your
  name).
- The `ARTICLE.md` narrative sections are placeholders (`[TBD]`) pending
  real numbers — see the note at the top of that file.

## Assumptions made

- CognoDB's advertised free-tier RAM is ambiguous between the PDF (256MB)
  and the live site (512MB) — capped comparison platforms at 512MB and
  documented the discrepancy rather than picking one silently (see README
  Fairness section).
- "Same dataset" was read as same graph *structure*; synthetic per-node
  properties were treated as acceptable/necessary scaffolding since the raw
  SNAP data has none, and are clearly labeled as synthetic everywhere they
  appear.
- Driver-batched loading (not vendor-specific bulk-import tools) was chosen
  as the one loading method guaranteed available on every platform,
  favoring cross-platform fairness over each vendor's best-case ingest
  number.

## Session 2 (2026-08-20): pre-flight gap review, before running against real CognoDB

Re-read the PDF requirement-by-requirement against the actual code (not just
the README's claims about it) before starting the real CognoDB setup. Found
and fixed:

- **Failure isolation.** Previously, one failed query/category/concurrency
  level would raise an uncaught exception and `write_result` (called only at
  the end of `main()`) would never run — silently discarding every
  already-collected category for that platform, and (on `run_all.sh`, which
  had `set -e`) aborting the rest of the pipeline too. Now every load step,
  workload category, and mixed-workload concurrency level is individually
  wrapped; failures are recorded as `{"error": "..."}` in the results JSON
  and the harness moves on. `run_all.ps1`/`run_all.sh` now summarize which
  steps failed at the end instead of dying on the first one. This is what
  makes the assignment's "record every caveat honestly... timeouts, failed
  runs" actually true under a real, occasionally-throttled free-tier
  connection, rather than aspirational.
- **Cold-start latency** (`cold_start_ms`) is now captured — the first query
  on a fresh connection, before the warm-up loop — and rendered in its own
  README table, addressing the "separate warm vs. cold numbers" trait from
  the assignment's "what a strong submission looks like" section.
- **Post-load count verification** (`verified_node_count`/`verified_edge_count`)
  — each loader now re-queries the platform after loading and compares
  against the source CSV counts, so "identical dataset on every platform" is
  a checked fact in the README table, not an assumption.
- **RAM ambiguity resolved.** Fetched cognodb.com/pricing directly (2026-08-20):
  free tier is 512MB RAM / burst 0.5 vCPU / 1GB disk / 200 connections / 500
  IOPS. README now cites this instead of leaving the PDF's "256MB" vs. the
  site's "512MB" as an open question.
- **`scripts/check_connections.py` added** — a pre-flight smoke test for all
  5 platforms, so a bad `.env` value or a container that isn't up yet is
  caught in seconds instead of partway through a 20+ minute run.
- Fixed a stale comment in `download_dataset.py` (said ~183,831 edges; the
  pipeline actually loads all 367,662 directed edges — the directed/undirected
  distinction was already explained in the README, the docstring just hadn't
  been updated to match).
- All changes verified: `python -m py_compile` clean on every touched file,
  `pytest tests/` 5/5, and `aggregate_results.py`'s new table logic (verified-count
  mismatch detection, per-category/per-concurrency error rendering, cold-start
  table) dry-run tested against synthetic results in an isolated scratch copy
  — the real `README.md`/`results/` were not touched by that test.

## Session 3 (2026-08-20): first real run surfaced a genuine loader bug

Set up CognoDB Cloud (`db-51aaa980`, `us-east4`, v0.9.11) and the Docker
stack, confirmed all 5 platforms reachable via `check_connections.py`, then
kicked off the real `scripts/run_all.ps1` run. Two real findings:

- **CognoDB's edge load failed: 36,692 nodes loaded, but 0 relationships
  landed**, with `Neo.TransientError.General.OutOfTimeError — context
  deadline exceeded`. Confirmed independently from the CognoDB console
  itself (Overview tab showed Nodes: 36,692, Relationships: 0).
- **Root cause, not just "free tier is slow":** `load_cypher_family.py` and
  `load_falkordb.py` created the `Person.id` index/constraint *after*
  loading edges, not before. Every edge insert does `MATCH (a:Person {id:
  ...}), (b:Person {id: ...})` to find its endpoints — without an index
  that's a full label scan per lookup, twice per edge, across 367,662
  edges. Locally this made Neo4j's load take 12+ minutes (never finished
  before being killed) instead of the ~1 minute it should take; against
  CognoDB's burst-limited 0.5vCPU free tier it was slow enough to hit the
  server's own query timeout.
- **Fixed:** both loaders now create indexes immediately after node load
  and before edge load, with a new `index_creation_seconds` field reported
  separately from `edge_load_seconds` so the README's load table shows
  exactly how much time indexing itself took per platform. Verified fix:
  re-ran Neo4j's loader alone, total load time 12+ min (incomplete) →
  57.2s, with `verified_edge_count` now matching the source exactly
  (367,662/367,662). ArangoDB's loader was never affected (it inserts by
  explicit `_from`/`_to` keys, no `MATCH` lookup involved).
- Also caught and fixed a real Docker Compose bug unrelated to the above:
  `docker-compose.yml`'s FalkorDB service used `command: ["--maxmemory",
  "400mb"]`, which replaced the image's default CMD (a script that builds
  the `redis-server ... --loadmodule falkordb.so` invocation from
  `REDIS_ARGS`/`FALKORDB_ARGS` env vars) — the container ran as plain
  Redis with the graph module never loaded (`GRAPH.QUERY` → "unknown
  command", `MODULE LIST` empty). Fixed by setting `REDIS_ARGS` and
  `BROWSER=0` as environment variables instead of overriding `command:`.
- Also noted for the README's caveats: the public `arangodb:3.12` Docker
  Hub image resolves to Enterprise Edition (confirmed from its own startup
  log), not Community — not a deliberate choice, just what the tag
  resolves to, but worth disclosing.
- Housekeeping: accidentally ran the first `pip install -r requirements.txt`
  against the global Python instead of a venv, downgrading numpy/matplotlib/
  pytest/python-dotenv already installed there. Caught immediately, restored
  the original global versions, then created `.venv` properly and moved the
  project's dependencies there. No lasting effect, but worth remembering:
  always use `.venv` for this project, never the global interpreter.

**Not yet done, flagged as optional given the 48h window:** run-to-run
variance (running the full pipeline N times and reporting spread) — the
assignment lists this as a "strong submission" trait, not a requirement.
Deferred pending a decision on whether there's time after the first full run.

## Suggested next steps (for you)

1. Sign up at console.cognodb.com/signup, create the free c0 instance, copy
   the URI + password into `.env`.
2. Install Docker Desktop if not already present; `docker compose up -d`
   from the project root.
3. `pip install -r requirements.txt`, then run `scripts/run_all.ps1`.
4. Skim the regenerated `README.md` Results section and fill in
   `ARTICLE.md`'s `[TBD]` narrative paragraphs against the real numbers.
5. `git init`, commit, push to a new public GitHub repo.
6. Email the repo URL to hr@wexa.ai with the required subject line —
   you send this yourself.
