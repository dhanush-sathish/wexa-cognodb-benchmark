"""
Smoke tests for the parts of the harness that don't require a live database
connection. Run with: pytest tests/
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from common import stats  # noqa: E402
from common.dataset_meta import DEPARTMENTS  # noqa: E402


def test_timer_percentiles():
    timer = stats.Timer()
    for delay in [0.001, 0.002, 0.003, 0.004, 0.005]:
        with timer.measure():
            time.sleep(delay)
    result = timer.percentiles()
    assert result["n"] == 5
    assert result["p50_ms"] > 0
    assert result["p95_ms"] >= result["p50_ms"]


def test_timer_empty():
    timer = stats.Timer()
    result = timer.percentiles()
    assert result["n"] == 0
    assert result["p50_ms"] is None


def test_write_result_merges(tmp_path):
    stats.write_result(tmp_path, "testplatform", {"a": 1})
    path = stats.write_result(tmp_path, "testplatform", {"b": 2})
    data = json.loads(path.read_text())
    assert data["a"] == 1
    assert data["b"] == 2
    assert data["platform"] == "testplatform"


def test_departments_fixed_list():
    assert len(DEPARTMENTS) == 10
    assert len(set(DEPARTMENTS)) == 10


def test_dataset_prepared():
    processed = Path(__file__).resolve().parents[1] / "data" / "processed"
    stats_path = processed / "dataset_stats.json"
    assert stats_path.exists(), "run `python data/prepare_dataset.py` first"
    data = json.loads(stats_path.read_text())
    assert data["edge_count"] >= 100_000
    assert data["node_count"] > 0
