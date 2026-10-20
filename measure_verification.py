#!/usr/bin/env python3
"""Measure local verification effort separately from search and torch probes."""
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from verifier import load, verify

ROOT = Path(__file__).resolve().parent


def main():
    rows = load(ROOT / "records/frontiers.json")
    entries = {e["id"]: e for e in load(ROOT / "benchmarks/suite.json")["graphs"]}
    graph_cache = {key: load(ROOT / e["path"]) for key, e in entries.items()}
    samples = []
    for row in rows:
        for _ in range(7):
            t = time.perf_counter_ns()
            verify(graph_cache[row["graph"]], load(ROOT / row["object"]), row["budget"])
            samples.append((time.perf_counter_ns() - t) / 1e6)
    t = time.perf_counter()
    run = subprocess.run([sys.executable, "verify_all.py"], cwd=ROOT, capture_output=True,
                         text=True, check=True, timeout=120)
    elapsed = time.perf_counter() - t
    (ROOT / "research/initial/validation.log").write_text(run.stdout + run.stderr)
    report = {
        "python": platform.python_version(), "platform": platform.platform(),
        "scope": "Graph objects cached; each certificate read/parsed then verified; 7 repeats per row. Full command separately includes process startup, tests, exact solves and task controls.",
        "timing_caveat": "Separate from this task's search and PyTorch probes. Other system load is unmonitored; descriptive local costs, not cross-machine guarantees.",
        "samples": len(samples), "certificate_median_ms": statistics.median(samples),
        "certificate_p95_ms": sorted(samples)[int(.95 * (len(samples)-1))],
        "certificate_max_ms": max(samples), "full_verify_all_seconds": elapsed,
        "command": [sys.executable, "verify_all.py"], "all_samples_ms": samples
    }
    (ROOT / "research/initial/verification-cost.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "all_samples_ms"}, indent=2))


if __name__ == "__main__":
    main()
