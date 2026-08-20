"""
Downloads the SNAP email-Enron dataset (public domain, Stanford Network Analysis
Project). Source: https://snap.stanford.edu/data/email-Enron.html

Nodes are anonymized Enron email addresses (int IDs). An edge i->j means i sent
at least one email to j. The raw file has ~36,692 nodes and ~183,831
*undirected* communicating pairs, but lists both directions of each pair as
separate directed lines -- data/prepare_dataset.py keeps that directed
representation as-is (367,662 directed edges), which still fits comfortably
inside a 1GB / 512MB-RAM free tier and sits inside the assignment's suggested
100k-500k relationship range. See README.md's Dataset section for why the
directed and undirected counts differ.
"""
import gzip
import shutil
import urllib.request
from pathlib import Path

SOURCE_URL = "https://snap.stanford.edu/data/email-Enron.txt.gz"
RAW_DIR = Path(__file__).parent / "raw"
GZ_PATH = RAW_DIR / "email-Enron.txt.gz"
TXT_PATH = RAW_DIR / "email-Enron.txt"


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if TXT_PATH.exists():
        print(f"Already present: {TXT_PATH}")
        return TXT_PATH

    print(f"Downloading {SOURCE_URL} ...")
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "cognodb-benchmark/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(GZ_PATH, "wb") as out:
        shutil.copyfileobj(resp, out)

    print(f"Decompressing to {TXT_PATH} ...")
    with gzip.open(GZ_PATH, "rt") as gz_in, open(TXT_PATH, "w", encoding="utf-8") as out:
        shutil.copyfileobj(gz_in, out)

    print("Done.")
    return TXT_PATH


if __name__ == "__main__":
    download()
