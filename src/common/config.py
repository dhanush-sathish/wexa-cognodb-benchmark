import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

PROCESSED_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
CHARTS_DIR = ROOT / "charts"


@dataclass
class BoltTarget:
    name: str
    uri: str
    user: str
    password: str


def cognodb() -> BoltTarget:
    return BoltTarget("cognodb", os.environ["COGNODB_URI"], os.environ.get("COGNODB_USER", "cognodb"),
                       os.environ["COGNODB_PASSWORD"])


def neo4j() -> BoltTarget:
    return BoltTarget("neo4j", os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                       os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))


def memgraph() -> BoltTarget:
    return BoltTarget("memgraph", os.environ.get("MEMGRAPH_URI", "bolt://localhost:7688"),
                       os.environ.get("MEMGRAPH_USER", ""), os.environ.get("MEMGRAPH_PASSWORD", ""))


BOLT_TARGETS = {
    "cognodb": cognodb,
    "neo4j": neo4j,
    "memgraph": memgraph,
}


def falkordb_config():
    return {
        "host": os.environ.get("FALKORDB_HOST", "localhost"),
        "port": int(os.environ.get("FALKORDB_PORT", 6379)),
        "graph": os.environ.get("FALKORDB_GRAPH", "benchmark"),
    }


def arangodb_config():
    return {
        "url": os.environ.get("ARANGODB_URL", "http://localhost:8529"),
        "user": os.environ.get("ARANGODB_USER", "root"),
        "password": os.environ.get("ARANGODB_PASSWORD", ""),
        "db": os.environ.get("ARANGODB_DB", "benchmark"),
    }
