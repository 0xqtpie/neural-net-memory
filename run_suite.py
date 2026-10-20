#!/usr/bin/env python3
"""Build or check all frozen graph/budget records."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time

from search import baseline_candidates, certificate, exact, optimize
from verifier import digest, load, require, verify

ROOT = Path(__file__).resolve().parent


def write(path, data):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def filehash(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def local_bound(g):
    """Every op must execute once with all distinct inputs plus output resident."""
    sizes = {n["id"]: n["bytes"] for n in g["inputs"] + g["nodes"]}
    fixed = {n["id"] for n in g["inputs"]}
    sets = [fixed | set(n["deps"]) | {n["id"]} for n in g["nodes"]]
    sets += [fixed | set(n["backward_requires"]) for n in g["nodes"]]
    sets += [fixed | set(g["outputs"])]
    return max(sum(sizes[x] for x in s) for s in sets)


def build(iterations, seeds):
    suite = load(ROOT / "benchmarks/suite.json")
    rows, baselines, experiments, timings = [], [], [], []
    for entry in suite["graphs"]:
        started = time.perf_counter()
        g = load(ROOT / entry["path"])
        require(digest(g) == entry["sha256"], "graph drift")
        ceiling = sum(n["cost"] for n in g["nodes"]) * (len(g["nodes"]) + 1) ** 2
        candidates = []
        for method, actions in baseline_candidates(g):
            c = certificate(g, actions, ceiling, method)
            rel = f"certificates/baselines/{g['id']}/{method}.json"
            write(rel, c)
            baseline = {"graph": g["id"], "method": method, "object": rel,
                        "sha256": filehash(rel), **c["claims"]}
            baselines.append(baseline)
            candidates.append((baseline, c))
        search_runs = []
        for seed in seeds:
            t = time.perf_counter()
            found = optimize(g, entry["budgets"], seed, iterations)
            search_runs.append(found)
            experiments.append({"graph": g["id"], "seed": seed, "iterations": iterations,
                                "evaluated": next(iter(found.values()))["metadata"]["evaluated"],
                                "seconds": time.perf_counter() - t,
                                "points": [{"budget": b, **c["claims"]} for b, c in found.items()]})
            for budget, c in found.items():
                write(f"certificates/search/{g['id']}/seed{seed}-b{budget}.json", c)
        for budget in entry["budgets"]:
            feasible = [(b, c) for b, c in candidates if b["recompute_cost"] <= budget]
            base, base_c = min(feasible, key=lambda pair: (
                pair[0]["peak_bytes"], pair[0]["recompute_cost"], pair[0]["method"]))
            search_c = min((found[budget] for found in search_runs), key=lambda c: (
                c["claims"]["peak_bytes"], c["claims"]["recompute_cost"], len(c["actions"])))
            first_three_peak = min(base["peak_bytes"], *(
                found[budget]["claims"]["peak_bytes"] for found in search_runs[:3]))
            best = min([base_c, search_c], key=lambda c: (
                c["claims"]["peak_bytes"], c["claims"]["recompute_cost"]))
            bound = local_bound(g)
            exact_seconds = None
            if entry["exact"]:
                t = time.perf_counter()
                best = exact(g, budget)
                exact_seconds = time.perf_counter() - t
                bound = best["claims"]["peak_bytes"]
            best = dict(best, budget=budget)
            verify(g, best, budget)
            rel = f"certificates/frontier/{g['id']}-b{budget}.json"
            write(rel, best)
            measured = []
            for _ in range(5):
                t = time.perf_counter_ns()
                verify(g, load(ROOT / rel), budget)
                measured.append((time.perf_counter_ns() - t) / 1e6)
            timings.append({"graph": g["id"], "budget": budget, "certificate_bytes": (ROOT / rel).stat().st_size,
                            "actions": len(best["actions"]), "verify_ms_samples": measured,
                            "exact_seconds": exact_seconds})
            row = {"graph": g["id"], "family": entry["family"], "budget": budget,
                   "peak_bytes": best["claims"]["peak_bytes"],
                   "recompute_cost": best["claims"]["recompute_cost"], "lower_bound": bound,
                   "bound_method": "exact-minimax" if entry["exact"] else "mandatory-local-allocation",
                   "optimal": best["claims"]["peak_bytes"] == bound,
                   "object": rel, "sha256": filehash(rel), "method": best["method"],
                   "baseline_peak": base["peak_bytes"], "baseline_method": base["method"],
                   "baseline_object": base["object"],
                   "search_peak": search_c["claims"]["peak_bytes"],
                   "first_three_seeds_incumbent_peak": first_three_peak,
                   "later_seeds_improved": min(base["peak_bytes"], search_c["claims"]["peak_bytes"]) < first_three_peak,
                   "improved_over_baseline": best["claims"]["peak_bytes"] < base["peak_bytes"],
                   "search_improved_over_baseline": search_c["claims"]["peak_bytes"] < base["peak_bytes"],
                   "by": ["Codex local initialization"], "source": "research/initial/REPORT.md",
                   "updated": "2026-10-20", "evidence_level": ["author-checked"]}
            rows.append(row)
        print(f"BUILT {g['id']}: {len(entry['budgets'])} rows in {time.perf_counter()-started:.2f}s", flush=True)
    write("records/frontiers.json", rows)
    write("records/baselines.json", baselines)
    # Non-dominated points in the discovered set, not an assertion of complete frontier.
    pareto = {}
    for entry in suite["graphs"]:
        points = [r for r in rows if r["graph"] == entry["id"]]
        pareto[entry["id"]] = [
            {"budget": r["budget"], "recompute_cost": r["recompute_cost"], "peak_bytes": r["peak_bytes"],
             "object": r["object"]}
            for r in points if not any(
                (s["peak_bytes"] <= r["peak_bytes"] and s["recompute_cost"] <= r["recompute_cost"]
                 and (s["peak_bytes"], s["recompute_cost"]) != (r["peak_bytes"], r["recompute_cost"]))
                or (s["peak_bytes"], s["recompute_cost"]) == (r["peak_bytes"], r["recompute_cost"])
                and s["budget"] < r["budget"] for s in points)]
    write("records/pareto.json", pareto)
    realistic = [r for r in rows if r["family"] != "synthetic"]
    summary = {
        "graphs": len(suite["graphs"]), "challenges": len(rows), "baseline_certificates": len(baselines),
        "exact_challenges": sum(e["exact"] * len(e["budgets"]) for e in suite["graphs"]),
        "seeds": seeds, "iterations_per_graph_seed": iterations,
        "search_evaluations": sum(x["evaluated"] for x in experiments),
        "search_seconds": sum(x["seconds"] for x in experiments),
        "improved_challenges": sum(r["improved_over_baseline"] for r in rows),
        "heuristic_improved_challenges": sum(r["search_improved_over_baseline"] for r in rows),
        "realistic_challenges": len(realistic),
        "realistic_improved_challenges": sum(r["improved_over_baseline"] for r in realistic),
        "realistic_graphs_improved": len({r["graph"] for r in realistic if r["improved_over_baseline"]}),
        "realistic_later_seed_improvements": sum(r["later_seeds_improved"] for r in realistic),
        "realistic_unclosed_gaps": sum(not r["optimal"] for r in realistic),
        "max_realistic_reduction_percent": max(100 * (1-r["peak_bytes"]/r["baseline_peak"]) for r in realistic),
        "verification_median_ms": statistics.median(
            statistics.median(t["verify_ms_samples"]) for t in timings),
        "verification_max_sample_ms": max(max(t["verify_ms_samples"]) for t in timings),
        "certificate_total_bytes": sum(t["certificate_bytes"] for t in timings),
        "max_certificate_actions": max(t["actions"] for t in timings),
        "interpretation": f"Best of {len(seeds)} seeds against all segment widths plus included baselines; not SOTA or independent-agent yield.",
    }
    write("research/initial/measurements.json", {
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "processor": platform.machine(), "gpu_used": False},
        "timing_note": "Descriptive local wall-clock samples, not controlled hardware performance claims; system load unmonitored.",
        "summary": summary, "search_runs": experiments, "verification": timings})
    print(json.dumps(summary, indent=2))


def check(graph=None, budget=None, prove=False):
    suite = load(ROOT / "benchmarks/suite.json")
    entries = {e["id"]: e for e in suite["graphs"]}
    rows = load(ROOT / "records/frontiers.json")
    keys = {(r["graph"], r["budget"]) for r in rows}
    expected = {(e["id"], b) for e in entries.values() for b in e["budgets"]}
    require(keys == expected and len(rows) == len(keys), "missing/duplicate/extra challenge rows")
    baseline_rows = load(ROOT / "records/baselines.json")
    verified_baselines = {}
    for b in baseline_rows:
        if graph is not None and b["graph"] != graph:
            continue
        e = entries[b["graph"]]
        g = load(ROOT / e["path"])
        require(digest(g) == e["sha256"], "graph hash changed")
        require(filehash(b["object"]) == b["sha256"], "baseline hash changed")
        metrics = verify(g, load(ROOT / b["object"]))
        require(all(b[k] == v for k, v in metrics.items()), "baseline record differs")
        verified_baselines[b["object"]] = b
    selected = [r for r in rows if (graph is None or r["graph"] == graph)
                and (budget is None or r["budget"] == budget)]
    require(bool(selected), "no matching row")
    for r in selected:
        entry = entries[r["graph"]]
        g = load(ROOT / entry["path"])
        require(digest(g) == entry["sha256"], "graph hash changed")
        require(filehash(r["object"]) == r["sha256"], "certificate hash changed")
        metrics = verify(g, load(ROOT / r["object"]), r["budget"])
        require(metrics["peak_bytes"] == r["peak_bytes"] and metrics["recompute_cost"] == r["recompute_cost"],
                "frontier row disagrees with certificate")
        feasible = [b for b in verified_baselines.values()
                    if b["graph"] == r["graph"] and b["recompute_cost"] <= r["budget"]]
        require(r["baseline_peak"] == min(b["peak_bytes"] for b in feasible), "baseline frontier mismatch")
        b = verified_baselines[r["baseline_object"]]
        require(b["peak_bytes"] == r["baseline_peak"] and b["recompute_cost"] <= r["budget"],
                "referenced baseline infeasible")
        require(r["improved_over_baseline"] == (r["peak_bytes"] < r["baseline_peak"]), "false yield claim")
        require(r["lower_bound"] <= r["peak_bytes"], "bound above witness")
        require(r["optimal"] == (r["lower_bound"] == r["peak_bytes"]), "optimal flag inconsistent")
        if entry["exact"]:
            if prove:
                optimum = exact(g, r["budget"])["claims"]["peak_bytes"]
                require(optimum == r["lower_bound"] == r["peak_bytes"], "incorrect exact optimum")
        else:
            require(r["lower_bound"] == local_bound(g), "incorrect local lower bound")
        # Check every seed certificate and the recorded heuristic comparison.
        found = list((ROOT / f"certificates/search/{r['graph']}").glob(f"seed*-b{r['budget']}.json"))
        require(bool(found), "missing search certificates")
        scores = [verify(g, load(p), r["budget"])["peak_bytes"] for p in found]
        require(min(scores) == r["search_peak"], "search record mismatch")
        require(r["search_improved_over_baseline"] == (min(scores) < r["baseline_peak"]), "false search yield")
    print(f"PASS: {len(selected)} frontier rows; {len(verified_baselines)} baseline certificates; "
          f"exact optimality {'recomputed' if prove else 'not rerun (witness check only)'}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["build", "check"])
    p.add_argument("--iterations", type=int, default=600)
    p.add_argument("--seeds", type=int, nargs="+", default=list(range(20261020, 20261026)))
    p.add_argument("--graph")
    p.add_argument("--budget", type=int)
    p.add_argument("--exact", action="store_true")
    args = p.parse_args()
    if args.mode == "build":
        build(args.iterations, args.seeds)
    else:
        check(args.graph, args.budget, args.exact)


if __name__ == "__main__":
    main()
