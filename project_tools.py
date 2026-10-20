#!/usr/bin/env python3
"""Local catalogue controls: task draw, source index, positive controls, and audit."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys

from verifier import load, require

ROOT = Path(__file__).resolve().parent


def pick(seed):
    seed = seed or secrets.token_hex(16)
    require(re.fullmatch(r"[0-9a-fA-F]{32}", seed) is not None, "seed must be 32 hex digits")
    catalog = load(ROOT / "discover/catalog.json")
    draw = int(seed[:8], 16) % 100
    for track in catalog["tracks"]:
        draw -= track["weight"]
        if draw < 0:
            break
    task = track["tasks"][int(seed[8:16], 16) % len(track["tasks"])]
    result = {"seed": seed.lower(), "track": track["id"], "task": task["id"],
              "question": task["question"], "first_step": task["first_step"]}
    if "rows" in task:
        rows = load(ROOT / "records/frontiers.json")
        where = task["rows"].get("where", {})
        rows = [r for r in rows if (not task["rows"].get("open", True) or not r["optimal"])
                and all(str(r[k]) == str(v) for k, v in where.items())]
        require(bool(rows), "no eligible rows; revise catalogue")
        result["row"] = rows[int(seed[16:24], 16) % len(rows)]
    now = datetime.now(timezone.utc)
    live = [c for c in load(ROOT / "discover/claims.json")
            if datetime.fromisoformat(c["expires"].replace("Z", "+00:00")) > now]
    result["live_claims"] = live
    result["coordination_note"] = "Local advisory claims only; inspect overlap before starting. No claim written."
    print(json.dumps(result, indent=2))


def check_sources():
    sources = load(ROOT / "research/sources.json")
    require(len(sources) >= 8, "source list incomplete")
    require(len({s["id"] for s in sources}) == len(sources), "duplicate sources")
    require(all(s["url"].startswith("https://") and s["checked_on"] == "2026-10-20"
                and s["status"] for s in sources), "bad source metadata")
    require((ROOT / "LITERATURE.md").exists(), "missing audit")
    print(f"PASS: {len(sources)} primary-source index entries; this checks metadata, not literature conclusions")


def controls():
    cat = load(ROOT / "discover/catalog.json")
    require(sum(t["weight"] for t in cat["tracks"]) == 100, "weights do not sum to 100")
    count = 0
    for track in cat["tracks"]:
        for task in track["tasks"]:
            command = task["first_step"]["command"]
            if command[0] == "python3":
                command = [sys.executable] + command[1:]
            p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
            require(p.returncode == 0 and task["first_step"]["expected"] in p.stdout + p.stderr,
                    f"card {task['id']} failed: {p.stdout}\n{p.stderr}")
            count += 1
    print(f"PASS: all {count} catalogue first_step positive controls")


def summary_check():
    rows = load(ROOT / "records/frontiers.json")
    baselines = load(ROOT / "records/baselines.json")
    realistic = [r for r in rows if r["family"] != "synthetic"]
    measurements = load(ROOT / "research/initial/measurements.json")
    s = measurements["summary"]
    checks = {
        "graphs": len({r["graph"] for r in rows}), "challenges": len(rows),
        "baseline_certificates": len(baselines),
        "exact_challenges": sum(r["bound_method"] == "exact-minimax" for r in rows),
        "improved_challenges": sum(r["improved_over_baseline"] for r in rows),
        "heuristic_improved_challenges": sum(r["search_improved_over_baseline"] for r in rows),
        "realistic_challenges": len(realistic),
        "realistic_improved_challenges": sum(r["improved_over_baseline"] for r in realistic),
        "realistic_graphs_improved": len({r["graph"] for r in realistic if r["improved_over_baseline"]}),
        "realistic_unclosed_gaps": sum(not r["optimal"] for r in realistic),
        "realistic_later_seed_improvements": sum(r["later_seeds_improved"] for r in realistic),
        "search_evaluations": sum(x["evaluated"] for x in measurements["search_runs"]),
    }
    require(all(s[k] == v for k, v in checks.items()), "summary inconsistent with records")
    for artifact in load(ROOT / "discover/frontier.json").get("artifacts", []):
        actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
        require(actual == artifact["sha256"], f"frontier artifact hash changed: {artifact['path']}")
    for r in rows:
        peaks = []
        for seed in s["seeds"]:
            c = load(ROOT / f"certificates/search/{r['graph']}/seed{seed}-b{r['budget']}.json")
            peaks.append(c["claims"]["peak_bytes"])
        first = min(r["baseline_peak"], *peaks[:3])
        require(r["first_three_seeds_incumbent_peak"] == first, "first-stage score incorrect")
        require(r["later_seeds_improved"] == (min(r["baseline_peak"], *peaks) < first),
                "marginal yield incorrect")
    pareto = load(ROOT / "records/pareto.json")
    require(set(pareto) == {r["graph"] for r in rows}, "Pareto graph coverage mismatch")
    for name, points in pareto.items():
        candidates = {(r["recompute_cost"], r["peak_bytes"]) for r in rows if r["graph"] == name}
        nondominated = {p for p in candidates if not any(
            q != p and q[0] <= p[0] and q[1] <= p[1] for q in candidates)}
        require({(p["recompute_cost"], p["peak_bytes"]) for p in points} == nondominated,
                "incorrect discovered Pareto set")
    # Every integer segment width and each comparator must be represented.
    suite = load(ROOT / "benchmarks/suite.json")
    for entry in suite["graphs"]:
        g = load(ROOT / entry["path"])
        expected = {"eager", "recompute-on-demand", "selective-save-expensive"}
        expected |= {f"{kind}-{w}" for kind in ("segment", "checkpoint-sequential")
                     for w in range(1, len(g["nodes"]) + 1)}
        found = [b["method"] for b in baselines if b["graph"] == g["id"]]
        require(set(found) == expected and len(found) == len(expected), "baseline coverage incomplete")
    print("PASS: discovery-yield summary and exhaustive segment-width baseline coverage")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["pick", "sources", "controls", "summary"])
    p.add_argument("--seed")
    args = p.parse_args()
    {"pick": lambda: pick(args.seed), "sources": check_sources, "controls": controls,
     "summary": summary_check}[args.command]()


if __name__ == "__main__":
    main()
