#!/usr/bin/env python3
"""Deterministic exact minimax search and seeded checkpoint-set optimization."""
import argparse
import heapq
import itertools
import json
import math
import random
from pathlib import Path

from verifier import MODEL, digest, load, simulate, validate_graph, verify


def certificate(g, actions, budget, method, metadata=None):
    c = {"model": MODEL, "graph_id": g["id"], "graph_sha256": digest(g),
         "budget": budget, "method": method, "metadata": metadata or {},
         "actions": actions, "claims": simulate(g, actions, budget)}
    verify(g, c, budget)
    return c


def exact(g, budget, max_states=2_000_000):
    """Dijkstra on a finite pebble-state graph, edge weight = transient live bytes.

    Independent bit-mask transitions, not verifier.simulate. Raising a resource
    limit never produces an optimum claim. The first popped goal minimizes peak.
    """
    validate_graph(g)
    ns = g["nodes"]
    n = len(ns)
    if n > 12:
        raise ValueError("exact solver limited to 12 nodes; use search for larger graphs")
    if type(budget) is not int or budget < 0:
        raise ValueError("budget must be a nonnegative integer")
    index = {v["id"]: i for i, v in enumerate(ns)}
    mask = lambda names: sum(1 << index[x] for x in names if x in index)
    deps = [mask(v["deps"]) for v in ns]
    reqs = [mask(v["backward_requires"]) for v in ns]
    children = [mask([v["id"] for v in ns if x["id"] in v["deps"]]) for x in ns]
    outputs = mask(g["outputs"])
    full = (1 << n) - 1
    fixed = sum(x["bytes"] for x in g["inputs"])
    memory = [fixed] * (1 << n)
    for bits in range(1, 1 << n):
        low = bits & -bits
        memory[bits] = memory[bits ^ low] + ns[low.bit_length() - 1]["bytes"]
    # live, ever computed, backward completed, loss barrier, recomputation spent
    start = (0, 0, 0, False, 0)
    best, prev = {start: fixed}, {}
    queue = [(fixed, start)]
    expanded = 0
    while queue:
        peak, state = heapq.heappop(queue)
        if best[state] != peak:
            continue
        live, seen, done, phase, spent = state
        expanded += 1
        if phase and done == full:
            actions, s = [], state
            while s != start:
                s, action = prev[s]
                actions.append(action)
            actions.reverse()
            c = certificate(g, actions, budget, "exact-minimax",
                            {"states": len(best), "expanded": expanded, "optimal": True})
            assert c["claims"]["peak_bytes"] == peak
            return c
        moves = []
        if not phase and seen == full and live & outputs == outputs:
            moves.append(((live, seen, done, True, spent), {"op": "loss"}))
        for i, node in enumerate(ns):
            bit = 1 << i
            if live & bit:
                moves.append(((live ^ bit, seen, done, phase, spent),
                              {"op": "drop", "node": node["id"]}))
            elif live & deps[i] == deps[i]:
                extra = node["cost"] if seen & bit else 0
                if (not (seen & bit) or node["recomputable"]) and spent + extra <= budget:
                    moves.append(((live | bit, seen | bit, done, phase, spent + extra),
                                  {"op": "forward", "node": node["id"]}))
            if phase and not done & bit and done & children[i] == children[i] and live & reqs[i] == reqs[i]:
                moves.append(((live, seen, done | bit, phase, spent),
                              {"op": "backward", "node": node["id"]}))
        for target, action in moves:
            score = max(peak, memory[target[0]])
            if score < best.get(target, math.inf):
                if len(best) >= max_states and target not in best:
                    raise RuntimeError(f"exact state limit {max_states} reached; NO optimality claim")
                best[target] = score
                prev[target] = (state, action)
                heapq.heappush(queue, (score, target))
    raise RuntimeError("no feasible schedule")


class Builder:
    """Constructive scheduler; final metrics always come from the standalone checker."""
    def __init__(self, g):
        self.g = g
        self.nodes = {n["id"]: n for n in g["nodes"]}
        self.inputs = {n["id"] for n in g["inputs"]}
        self.live = set(self.inputs)
        self.actions = []

    def emit(self, op, name=None):
        self.actions.append({"op": op, **({"node": name} if name is not None else {})})
        if op == "forward":
            self.live.add(name)
        elif op == "drop":
            self.live.remove(name)

    def clean(self, keep):
        for name in self.nodes:
            if name in self.live and name not in keep:
                self.emit("drop", name)

    def ensure(self, name, keep):
        if name in self.live:
            return
        protected = set(keep)
        for dep in self.nodes[name]["deps"]:
            self.ensure(dep, protected)
            protected.add(dep)
        self.emit("forward", name)
        self.clean(set(keep) | {name})

    def closure(self, names):
        result = set(names)
        stack = list(names)
        while stack:
            name = stack.pop()
            for dep in self.nodes.get(name, {}).get("deps", []):
                if dep not in result:
                    result.add(dep)
                    stack.append(dep)
        return result


def checkpoint_schedule(g, checkpoints, region_groups=None, save_final=False):
    """On-demand replay or segment replay; forward order is the listed DAG order."""
    b = Builder(g)
    ns = g["nodes"]
    keep = set(checkpoints) | {x["id"] for x in ns if not x["recomputable"]}
    groups = region_groups or []
    if groups:
        group_of = {name: i for i, group in enumerate(groups) for name in group}
        # Region inputs and backward cross-region references must survive the forward.
        for node in ns:
            for dep in node["deps"] + node["backward_requires"]:
                if dep in group_of and group_of[dep] != group_of[node["id"]]:
                    keep.add(dep)
        if save_final:
            keep |= set(groups[-1])
    for i, node in enumerate(ns):
        b.emit("forward", node["id"])
        future_inputs = {d for x in ns[i + 1:] for d in x["deps"]}
        b.clean(keep | future_inputs | set(g["outputs"]))
    b.emit("loss")
    if not groups:
        groups = [[x["id"]] for x in ns]
    remaining = {x["id"] for x in ns}
    for group in reversed(groups):
        needs = {r for name in remaining for r in b.nodes[name]["backward_requires"]}
        keep &= b.closure(needs)
        hold = set(keep)
        # Region replay retains all reconstructed saved values through region backward.
        for name in group:
            for req in b.nodes[name]["backward_requires"]:
                b.ensure(req, hold)
                hold.add(req)
        b.clean(hold)
        for name in reversed(group):
            b.emit("backward", name)
            remaining.remove(name)
            needs = {r for item in remaining for r in b.nodes[item]["backward_requires"]}
            hold &= b.closure(needs)
            keep &= hold
            b.clean(hold)
    return b.actions


def baseline_candidates(g):
    ns = g["nodes"]
    ids = [x["id"] for x in ns]
    required = {r for n in ns for r in n["backward_requires"]}
    candidates = [("eager", checkpoint_schedule(g, required)),
                  ("recompute-on-demand", checkpoint_schedule(g, set()))]
    # Tune every segment width, so discoveries do not merely beat an unlucky width.
    for width in range(1, len(ns) + 1):
        groups = [ids[i:i + width] for i in range(0, len(ids), width)]
        candidates.append((f"segment-{width}", checkpoint_schedule(g, set(), groups)))
        candidates.append((f"checkpoint-sequential-{width}",
                           checkpoint_schedule(g, set(), groups, save_final=True)))
    expensive = {x["id"] for x in ns if x.get("kind") in {"linear", "matmul", "conv"}}
    candidates.append(("selective-save-expensive", checkpoint_schedule(g, expensive)))
    return candidates


def optimize(g, budgets, seed=20261020, iterations=600):
    """Seeded population search over checkpoint sets; no global optimality claim.

    Maintains the best policy at every budget; explores single flips, multiple
    flips, and fresh random sets. Checkpoint schedules use a fixed topo/reverse order.
    """
    rng = random.Random(seed)
    ids = [x["id"] for x in g["nodes"]]
    max_budget = max(budgets)
    best = {}
    tried = set()
    evaluated = rejected = 0
    # Generous ceiling for measuring candidate cost before filtering budgets.
    ceiling = sum(x["cost"] for x in g["nodes"]) * (len(ids) + 1) ** 2
    def evaluate(keepers):
        nonlocal evaluated, rejected
        key = frozenset(keepers)
        if key in tried:
            return
        tried.add(key)
        actions = checkpoint_schedule(g, key)
        metrics = simulate(g, actions, ceiling)
        evaluated += 1
        if metrics["recompute_cost"] > max_budget:
            rejected += 1
        for budget in budgets:
            if metrics["recompute_cost"] <= budget:
                score = metrics["peak_bytes"], metrics["recompute_cost"], len(actions)
                if budget not in best or score < best[budget][0]:
                    best[budget] = (score, key, actions)
    evaluate(set(ids))
    evaluate(set())
    for width in range(2, min(10, len(ids)) + 1):
        evaluate(set(ids[::width]))
    for _ in range(iterations):
        if best and rng.random() < 0.8:
            keys = list(best.values())
            chosen = set(keys[rng.randrange(len(keys))][1])
            flips = 1 if rng.random() < 0.7 else rng.randint(2, min(5, len(ids)))
            for name in rng.sample(ids, flips):
                chosen.symmetric_difference_update({name})
        else:
            p = rng.random()
            chosen = {name for name in ids if rng.random() < p}
        evaluate(chosen)
    return {budget: certificate(g, record[2], budget, "seeded-checkpoint-search",
                                {"seed": seed, "iterations": iterations,
                                 "evaluated": evaluated, "over_max_budget": rejected,
                                 "checkpoints": sorted(record[1]), "optimal": False})
            for budget, record in best.items()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("graph")
    p.add_argument("--budget", type=int, required=True)
    p.add_argument("--method", choices=["exact", "search"], default="search")
    p.add_argument("--iterations", type=int, default=600)
    p.add_argument("--seed", type=int, default=20261020)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    graph = load(args.graph)
    result = exact(graph, args.budget) if args.method == "exact" else optimize(
        graph, [args.budget], args.seed, args.iterations)[args.budget]
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["claims"], sort_keys=True))


if __name__ == "__main__":
    main()
