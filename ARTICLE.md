# I Benchmarked CognoDB Against Four Other Graph Databases. Here's What Actually Happened.

*A candid, reproducible look at how a new managed graph database stacks up
against the field — code and raw numbers included.*

> **Status:** run for real on 2026-08-20 against a live CognoDB free
> instance and the full Docker stack. Every number below is quoted from
> that run's `results/*.json` — see [Status of this repo](README.md#status-of-this-repo)
> for exactly what ran and the two real bugs that were found and fixed
> along the way.

## Why bother benchmarking a database at all

Every graph database's landing page says it's fast. That's not information —
it's marketing copy. The only way to know whether a *specific* database is a
good fit for *your* workload is to load *your* kind of data, run *your* kind
of queries, and measure it yourself, under conditions you can actually
reproduce and someone else can actually check.

So that's what this is: CognoDB Cloud, a new managed graph database, run
head-to-head against four established graph databases — Neo4j, Memgraph,
FalkorDB, and ArangoDB — on the same dataset, the same queries, and the same
hardware envelope. Full methodology and every number are in the
[repo](README.md); this article is the readable version.

## The setup, in three sentences

We loaded the SNAP `email-Enron` social graph (36,692 people, 367,662
"sent an email to" relationships — real, public, and just the right size to
fit comfortably on a free-tier instance) into all five databases. We ran the
same six kinds of query against every one of them — point lookups, filtered
lookups, 1/2/3-hop traversals, and a grouped aggregation — 100 times each
after a warm-up, so we could report p50/p95 latency instead of a single
lucky number. Then we hammered all five with a mixed read/write workload at
increasing concurrency (1, 10, 40 clients at once) to see where each one's
throughput plateaus.

Everything ran on the same resource budget CognoDB gives away for free: half
a CPU core, half a gigabyte of RAM, a gigabyte of disk. No database got a
bigger box than any other — see [Fairness](README.md#fairness-resource-parity-across-every-platform)
for exactly how that was enforced with Docker resource limits.

## What we found

### Loading the data

The ingest numbers span **three orders of magnitude**, and the biggest
surprise isn't CognoDB. ArangoDB (12,450 relationships/sec) and FalkorDB
(13,450/sec) both loaded all 367,662 edges in about 30 seconds flat.
Neo4j came in at 7,329/sec (70 seconds total). CognoDB — the smallest, most
distant free instance in this whole comparison — managed 1,807/sec and
230 seconds total, which is exactly what you'd expect from a burst-limited
0.5vCPU box a continent away from the client. Slow, but it finished clean:
every node and edge it reported loading, it actually had, verified by an
independent count query afterward.

The real outlier is Memgraph: **55.5 relationships/sec, a 6,624-second
(~110 minute) total load** — running the *exact same* Cypher, over the
*exact same* Python driver code path, as Neo4j. We checked the obvious
explanation first: Memgraph's container was using only 138MB of its 512MB
limit when the load finished, so this isn't a database running out of
memory. Something in Memgraph's default write-durability behavior under
this specific resource cap is the more likely explanation — worth
independent verification before treating it as gospel, but it's a real,
reproducible number from this exact run, not a fluke.

### Reading the data: does hop depth hurt?

FalkorDB is in a different league here: 1/2/3-hop p50 latencies of 0.53,
0.79, and 1.14 milliseconds — its GraphBLAS/sparse-matrix engine is
purpose-built for exactly this. Neo4j and Memgraph both post reasonable
5-10ms p50s but a roughly **10x jump to p95** (Neo4j's hop_1: 6.1ms p50 vs.
81.0ms p95). That's not randomness — Neo4j's container was sitting at
99.14% of its memory cap by the end of the run, which is a textbook setup
for GC-driven latency spikes. ArangoDB holds a flat ~50ms across all three
hop depths — AQL traversal overhead, not graph size, dominates in this
range. CognoDB's 310-336ms numbers are, again, mostly the India-to-Virginia
network round trip talking, not the query engine — see the caveats below.

### Point lookups vs. filtered lookups

Every platform's index/constraint DDL actually succeeded this run (checked,
not assumed — see the repo's "Indexes actually created" table). Filtered
lookups cost roughly the same as point lookups everywhere, as you'd expect
from an indexed property scan — except Memgraph, where filtered lookup
(1.23ms p50) actually beat point lookup (6.93ms p50). We're not going to
oversell that as a real structural advantage; it's more likely favorable
cache/GC timing between the two test runs than a genuine pattern.

### Under concurrent load

This is where the platforms really separate — not by speed, but by *how
they fail*. CognoDB (3 → 30 → 107 ops/sec) and ArangoDB (21 → 189 → 231
ops/sec) both get *faster* as concurrency increases, for different
reasons: CognoDB because parallel clients hide its network latency,
ArangoDB because it's simply built for concurrent access. Neo4j stays
roughly flat (105 → 96 → 126) — capped by its own resource ceiling, not by
concurrency. Memgraph gets *worse* under load (65 → 26 → 28 ops/sec),
consistent with the same write-path cost we saw in its load numbers. And
FalkorDB — the fastest single-client reader in this entire benchmark by a
wide margin — goes from 1,235 ops/sec down to 550, then **fails outright**
at 40 clients with `Max pending queries exceeded`. That's not a slowdown,
it's a hard wall: FalkorDB's own module config caps it at 25 queued
queries. Blazing fast, low concurrency ceiling — a real trade-off, not a
flaw to average away.

## Where CognoDB stood out, and where it didn't

CognoDB didn't win on raw speed anywhere in this benchmark, and given a
free instance sitting a continent away on burst CPU, that's not a surprise.
Where it *did* hold up: every single number it reported was **correct** —
node and edge counts verified exactly, zero query errors across the entire
run, and its throughput scaled sensibly with concurrency exactly the way
you'd expect from a network-latency-bound service. In a benchmark that
also caught a real query bug in ArangoDB's traversal syntax and a real
write-performance cliff in Memgraph, "boring and correct" from the newest,
smallest product in the lineup is itself worth saying plainly. Where it
clearly lost: absolute latency (300ms+ for a point lookup that takes single
digits of milliseconds on the self-hosted platforms) — though how much of
that is "CognoDB" versus "the only region its free tier offered was 12,000km
from the client" is a fair question, and one this benchmark can't fully
separate. That asymmetry is real and is documented in the repo's caveats,
not glossed over.

## What this doesn't tell you

A few honest asterisks, because a benchmark without caveats is a benchmark
you shouldn't trust:

- This is one dataset, one shape of query, one point in time. A workload
  that looks completely different (huge properties, dense supernodes, heavy
  write contention) could reorder these results entirely.
- Everything ran on a free-tier-sized box on purpose, because that's what
  the assignment asked for and what anyone can reproduce for free — it is
  *not* a prediction of what happens at production scale on a paid tier.
- CognoDB is a new product; the other four have years of production
  tuning behind their default configs. That's a real, structural asymmetry
  worth remembering when reading any "new database vs. incumbents"
  comparison, this one included.

Full methodology, every raw JSON result, and the code to reproduce all of it
(or point it at your own dataset) is in the [repository](README.md).
