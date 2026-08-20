"""
Pre-flight smoke test: confirms all 5 platforms are reachable and can run a
trivial query, before committing to a full load + benchmark run that can take
20+ minutes. Does not touch results/ -- this is diagnostic only.

Usage:
    python scripts/check_connections.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from common import config  # noqa: E402


def check_bolt(name):
    from neo4j import GraphDatabase
    target = config.BOLT_TARGETS[name]()
    driver = GraphDatabase.driver(target.uri, auth=(target.user, target.password))
    try:
        driver.verify_connectivity()
        with driver.session() as session:
            session.run("RETURN 1 AS ok").consume()
        return True, target.uri
    finally:
        driver.close()


def check_falkordb():
    from falkordb import FalkorDB
    cfg = config.falkordb_config()
    db = FalkorDB(host=cfg["host"], port=cfg["port"])
    g = db.select_graph(cfg["graph"])
    g.query("RETURN 1")
    return True, f"{cfg['host']}:{cfg['port']}"


def check_arangodb():
    from arango import ArangoClient
    cfg = config.arangodb_config()
    client = ArangoClient(hosts=cfg["url"])
    sys_db = client.db("_system", username=cfg["user"], password=cfg["password"])
    sys_db.properties()
    return True, cfg["url"]


CHECKS = {
    "cognodb": lambda: check_bolt("cognodb"),
    "neo4j": lambda: check_bolt("neo4j"),
    "memgraph": lambda: check_bolt("memgraph"),
    "falkordb": check_falkordb,
    "arangodb": check_arangodb,
}


def main():
    print(f"{'Platform':<10} {'Status':<8} Detail")
    print("-" * 60)
    any_failed = False
    for name, check in CHECKS.items():
        try:
            ok, detail = check()
            print(f"{name:<10} {'OK':<8} {detail}")
        except Exception as e:
            any_failed = True
            print(f"{name:<10} {'FAIL':<8} {e}")
    print("-" * 60)
    if any_failed:
        print("One or more platforms are not reachable yet -- fix before running scripts/run_all.*")
        sys.exit(1)
    print("All 5 platforms reachable.")


if __name__ == "__main__":
    main()
