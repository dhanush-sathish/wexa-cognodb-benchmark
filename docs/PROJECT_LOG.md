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
