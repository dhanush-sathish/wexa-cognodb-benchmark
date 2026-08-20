"""
Canonical logical queries used by every platform's workload runner.

CognoDB, Neo4j and Memgraph all speak openCypher over Bolt, and FalkorDB speaks
Cypher over RESP -- so all four share the *same* Cypher strings below. ArangoDB
is the deliberate odd one out (AQL, not Cypher) -- this is the one place the
harness has to translate the logical query into a different language, which is
itself an honest data point about portability/lock-in, not just performance.

Index DDL is NOT shared here because Cypher dialects diverge the most on index
syntax (Neo4j 5 vs. Memgraph vs. FalkorDB) -- each loader creates its own
indexes and records exactly what it created in the results JSON.
"""

# ---- Cypher (CognoDB / Neo4j / Memgraph / FalkorDB) ----------------------

CYPHER_POINT_LOOKUP = "MATCH (p:Person {id: $id}) RETURN p.id AS id, p.email_hash AS email_hash, p.dept AS dept"

CYPHER_FILTERED_LOOKUP = "MATCH (p:Person {dept: $dept}) RETURN p.id AS id LIMIT 50"

CYPHER_HOP_1 = "MATCH (p:Person {id: $id})-[:EMAILED]->(n) RETURN DISTINCT n.id AS id LIMIT 100"

CYPHER_HOP_2 = "MATCH (p:Person {id: $id})-[:EMAILED]->()-[:EMAILED]->(n) RETURN DISTINCT n.id AS id LIMIT 100"

CYPHER_HOP_3 = ("MATCH (p:Person {id: $id})-[:EMAILED]->()-[:EMAILED]->()-[:EMAILED]->(n) "
                "RETURN DISTINCT n.id AS id LIMIT 100")

CYPHER_AGGREGATION = ("MATCH (p:Person)-[:EMAILED]->() "
                       "RETURN p.dept AS dept, count(*) AS outgoing_emails "
                       "ORDER BY outgoing_emails DESC")

CYPHER_WRITE_EDGE = ("MATCH (a:Person {id: $src}), (b:Person {id: $dst}) "
                      "CREATE (a)-[:EMAILED {seq: $seq}]->(b)")

# ---- AQL (ArangoDB) --------------------------------------------------------

AQL_POINT_LOOKUP = "FOR p IN persons FILTER p.id == @id RETURN {id: p.id, email_hash: p.email_hash, dept: p.dept}"

AQL_FILTERED_LOOKUP = "FOR p IN persons FILTER p.dept == @dept LIMIT 50 RETURN p.id"


# uniqueVertices: 'global' requires an explicit traversal order in this
# ArangoDB version ("uniqueVertices: 'global' is only supported, with
# order: bfs|weighted") -- bfs matches the logical semantics of the Cypher
# hop queries above (nearest-first, not depth-first).
AQL_HOP_1 = ("FOR v IN 1..1 OUTBOUND @start emailed "
             "OPTIONS {uniqueVertices: 'global', order: 'bfs'} LIMIT 100 RETURN v.id")

AQL_HOP_2 = ("FOR v IN 2..2 OUTBOUND @start emailed "
             "OPTIONS {uniqueVertices: 'global', order: 'bfs'} LIMIT 100 RETURN v.id")

AQL_HOP_3 = ("FOR v IN 3..3 OUTBOUND @start emailed "
             "OPTIONS {uniqueVertices: 'global', order: 'bfs'} LIMIT 100 RETURN v.id")

AQL_AGGREGATION = (
    "FOR p IN persons "
    "LET outgoing = LENGTH(FOR e IN emailed FILTER e._from == p._id RETURN 1) "
    "COLLECT dept = p.dept AGGREGATE outgoing_emails = SUM(outgoing) "
    "SORT outgoing_emails DESC "
    "RETURN {dept, outgoing_emails}"
)

AQL_WRITE_EDGE = "INSERT {_from: @from, _to: @to, seq: @seq} INTO emailed"
