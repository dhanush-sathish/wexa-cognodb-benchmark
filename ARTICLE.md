# I Benchmarked CognoDB Against Four Other Graph Databases. Here's What Actually Happened.

*A candid, reproducible look at how a new managed graph database stacks up
against the field — code and raw numbers included.*

> **Draft status:** this article is written and structured, but the numbers
> below are placeholders (`[TBD]`) until the benchmark is actually run
> against a live CognoDB instance and the local Docker stack — see the
> repo's [Status of this repo](README.md#status-of-this-repo) section. Every
> `[TBD]` in this file is filled in automatically by
> `python src/report/aggregate_results.py` once real results exist... well,
> almost automatically — the *numbers* get filled in by rerunning the
> aggregator against README.md; the *narrative* sentences around them still
> need a human pass to make sure the prose actually matches what happened.
> Do not publish this article with any `[TBD]` still in it.

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

`[TBD: nodes/sec and rels/sec table + one paragraph on which platform(s)
ingested fastest and whether any showed burstable-tier throttling partway
through]`

### Reading the data: does hop depth hurt?

`[TBD: p50/p95 chart description across 1/2/3-hop traversals — which
platform's latency grows the least as hop depth increases, and a plain-
language guess at why, tied to each engine's storage model]`

### Point lookups vs. filtered lookups

`[TBD: whether the indexed/filtered lookup cost noticeably more than the
point lookup on each platform, and whether every platform's index actually
got created — see the "Indexes actually created" table; call out honestly
if one platform's index DDL silently failed]`

### Under concurrent load

`[TBD: mixed-workload ops/sec at 1 / 10 / 40 clients per platform — which
ones kept scaling, which plateaued, and roughly where]`

## Where CognoDB stood out, and where it didn't

`[TBD — write this only after the numbers exist. If CognoDB wins something,
say so with the number. If it loses something, say that too, with the
number. The whole point of this exercise, per Wexa's own brief, was honest
methodology over a flattering result — so this section does not get to be
vague.]`

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
