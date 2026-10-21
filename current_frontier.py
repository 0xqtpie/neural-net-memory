"""Reconcile known trial results for task selection without rewriting experiments."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from verifier import load, require, verify

ROOT = Path(__file__).resolve().parent
TRIAL = ROOT / "research/trial-30m"


def verify_trial_bounds():
    """Recompute the trial's bound evidence without rewriting its frozen output."""
    sources = load(TRIAL / "SOURCES.json")["trial_sources_sha256"]
    for name in ("check_bounds.py", "dominance_exact.py"):
        require(hashlib.sha256((TRIAL / name).read_bytes()).hexdigest() == sources[name], "bound source hash mismatch")
    sys.path.insert(0, str(TRIAL))
    try:
        from check_bounds import zero_bound
        from dominance_exact import solve, selftest
        selftest()
        for bound in load(TRIAL / "bound-results.json")["bounds"]:
            graph = load(ROOT / f"benchmarks/graphs/{bound['graph']}.json")
            if bound["method"] == "zero-budget-mandatory-liveness":
                require(bound["budget"] == 0, "zero-budget proof used at nonzero budget")
                actual = zero_bound(graph)
                require(all(actual[k] == bound[k] for k in actual), "liveness proof differs")
            elif bound["method"] == "exact-dominance":
                certificate = solve(graph, bound["budget"], 500000, bound["lower_bound"])
                metrics = verify(graph, certificate, bound["budget"])
                require(metrics["peak_bytes"] == bound["lower_bound"], "exact bound differs")
            else:
                raise ValueError("unsupported bound method")
    finally:
        sys.path.pop(0)


def current_rows(root=ROOT):
    rows = load(root / "records/frontiers.json")
    indexed = {(r["graph"], r["budget"]): r for r in rows}
    require(len(indexed) == len(rows), "duplicate frontier row")
    seen = set()
    for proposal in load(root / "research/trial-30m/candidates.json"):
        key = proposal["graph"], proposal["budget"]
        require(key in indexed and key not in seen, "unknown or duplicate trial row")
        seen.add(key)
        row = indexed[key]
        path = (root / proposal["object"]).resolve()
        require(path.is_relative_to(root.resolve()), "certificate outside repository")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == proposal["sha256"], "trial certificate hash mismatch")
        metrics = verify(load(root / f"benchmarks/graphs/{key[0]}.json"), load(path), key[1])
        require(metrics["peak_bytes"] == proposal["peak_bytes"] and metrics["recompute_cost"] == proposal["recompute_cost"], "trial metrics mismatch")
        require(proposal["starting_peak"] == row["peak_bytes"], "trial baseline mismatch")
        require(proposal["peak_bytes"] < row["peak_bytes"], "trial must improve baseline")
        row["historical_peak_bytes"] = row["peak_bytes"]
        for field in ("peak_bytes", "recompute_cost", "object", "sha256", "method"):
            row[field] = proposal[field]
        row["source"] = "research/trial-30m/REPORT.md"
    for bound in load(root / "research/trial-30m/bound-results.json")["bounds"]:
        key = bound["graph"], bound["budget"]
        require(key in indexed, "bound for unknown row")
        row = indexed[key]
        if bound["lower_bound"] > row["lower_bound"]:
            row["lower_bound"] = bound["lower_bound"]
            row["bound_method"] = bound["method"]
            row["bound_source"] = "research/trial-30m/BOUNDS.md"
    for row in rows:
        require(row["lower_bound"] <= row["peak_bytes"], "bound contradicts witness")
        row["optimal"] = row["lower_bound"] == row["peak_bytes"]
        row["evidence_level"] = ["author-checked"]
        row["acceptance"] = "working target; independent review pending"
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write", action="store_true")
    p.add_argument("--bounds", action="store_true", help="Recompute recorded trial bounds and tiny cross-checks")
    p.add_argument("--graph")
    p.add_argument("--budget", type=int)
    a = p.parse_args()
    if a.bounds:
        verify_trial_bounds()
    rows = current_rows()
    target = ROOT / "records/working-frontiers.json"
    if a.write:
        target.write_text(json.dumps(rows, indent=2) + "\n")
    else:
        require(load(target) == rows, "working table stale; run current_frontier.py --write")
    selected = rows
    if a.graph is not None or a.budget is not None:
        require(a.graph is not None and a.budget is not None, "graph and budget required together")
        selected = [r for r in rows if (r["graph"], r["budget"]) == (a.graph, a.budget)]
        require(len(selected) == 1, "unknown challenge")
    for row in selected:
        path = ROOT / row["object"]
        require(hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"], "witness hash mismatch")
        metrics = verify(load(ROOT / f"benchmarks/graphs/{row['graph']}.json"), load(path), row["budget"])
        require(metrics["peak_bytes"] == row["peak_bytes"], "working score mismatch")
    print(json.dumps({"status": "PASS", "checked_rows": len(selected), "open_rows": sum(not r["optimal"] for r in rows), "evidence": "author-checked; bound proofs require separate review"}))


if __name__ == "__main__":
    main()
