#!/usr/bin/env python3
"""Standalone, standard-library-only certificate verifier for activation-memory/v1.

No import from the optimizer, generator, or PyTorch. All arithmetic is integer.
"""
import argparse
import hashlib
import json
from pathlib import Path

MODEL = "activation-memory/v1"


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def integer(x, minimum=0):
    return type(x) is int and x >= minimum


def digest(graph):
    return hashlib.sha256(json.dumps(graph, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def validate_graph(g):
    require(isinstance(g, dict) and g.get("model") == MODEL, "wrong graph model")
    require(isinstance(g.get("id"), str) and g["id"], "missing graph id")
    require(isinstance(g.get("inputs"), list) and g["inputs"], "inputs required")
    require(isinstance(g.get("nodes"), list) and g["nodes"], "nodes required")
    names = set()
    for item in g["inputs"] + g["nodes"]:
        require(isinstance(item, dict), "tensor must be object")
        name = item.get("id")
        require(isinstance(name, str) and name and name not in names, "duplicate/invalid tensor id")
        require(integer(item.get("bytes"), 1), "tensor bytes must be positive integer")
        names.add(name)
    available = {x["id"] for x in g["inputs"]}
    ancestors = {x: {x} for x in available}
    for node in g["nodes"]:
        deps = node.get("deps")
        require(isinstance(deps, list) and all(isinstance(x, str) for x in deps),
                "dependencies must be strings")
        require(len(set(deps)) == len(deps) and set(deps) <= available,
                "dependencies must form a topologically listed DAG")
        require(integer(node.get("cost"), 1) and integer(node.get("backward_cost"), 1),
                "costs must be positive integers")
        require(type(node.get("recomputable")) is bool, "recomputable must be boolean")
        req = node.get("backward_requires")
        require(isinstance(req, list) and all(isinstance(x, str) for x in req)
                and len(req) == len(set(req)), "bad backward requirements")
        a = {node["id"]}
        for dep in deps:
            a |= ancestors[dep]
        require(set(req) <= a, "backward may require only self/ancestors/inputs")
        ancestors[node["id"]] = a
        available.add(node["id"])
    used = {d for n in g["nodes"] for d in n["deps"]}
    sinks = {n["id"] for n in g["nodes"]} - used
    require(isinstance(g.get("outputs"), list) and all(isinstance(x, str) for x in g["outputs"])
            and len(set(g["outputs"])) == len(g["outputs"])
            and set(g["outputs"]) == sinks, "outputs must be exactly DAG sinks")
    return g


def simulate(graph, actions, budget, with_trace=False):
    """Check legality and return recomputed metrics; claims are checked separately."""
    validate_graph(graph)
    require(integer(budget), "budget must be a nonnegative integer")
    require(isinstance(actions, list) and len(actions) <= 1_000_000, "invalid/oversized schedule")
    nodes = {x["id"]: x for x in graph["nodes"]}
    inputs = {x["id"] for x in graph["inputs"]}
    sizes = {x["id"]: x["bytes"] for x in graph["inputs"] + graph["nodes"]}
    consumers = {x: set() for x in nodes}
    for n in nodes.values():
        for dep in n["deps"]:
            if dep in consumers:
                consumers[dep].add(n["id"])
    live, seen, done = set(inputs), set(), set()
    sealed = False
    peak = sum(sizes[x] for x in live)
    extra = forward = backward = 0
    trace = []
    for i, action in enumerate(actions):
        prefix = f"step {i}: "
        require(isinstance(action, dict), prefix + "action must be object")
        op = action.get("op")
        require(op in {"forward", "drop", "backward", "loss"}, prefix + "unknown action")
        if op == "loss":
            require(set(action) == {"op"}, prefix + "unexpected action fields")
            require(not sealed and seen == set(nodes), prefix + "incomplete/repeated loss barrier")
            require(set(graph["outputs"]) <= live, prefix + "loss output missing")
            sealed = True
        else:
            require(set(action) == {"op", "node"}, prefix + "unexpected action fields")
            name = action["node"]
            require(isinstance(name, str) and name in nodes, prefix + "unknown/immutable node")
            node = nodes[name]
            if op == "forward":
                require(name not in live, prefix + "cannot overwrite a live tensor")
                require(set(node["deps"]) <= live, prefix + "missing forward dependency")
                if name in seen:
                    require(node["recomputable"], prefix + "illegal recomputation")
                    extra += node["cost"]
                    require(extra <= budget, prefix + "recomputation budget exceeded")
                else:
                    require(not sealed, prefix + "new forward after loss")
                    seen.add(name)
                forward += node["cost"]
                # Output is allocated BEFORE any input can be dropped.
                live.add(name)
            elif op == "drop":
                require(name in live, prefix + "cannot drop absent tensor")
                live.remove(name)
            else:
                require(sealed, prefix + "backward before loss")
                require(name not in done, prefix + "duplicate backward")
                require(consumers[name] <= done, prefix + "missing downstream gradient")
                require(set(node["backward_requires"]) <= live, prefix + "missing backward activation")
                done.add(name)
                backward += node["backward_cost"]
        current = sum(sizes[x] for x in live)
        peak = max(peak, current)
        if with_trace:
            trace.append({"step": i, "live": sorted(live), "live_bytes": current,
                          "peak_bytes": peak, "recompute_cost": extra})
    require(sealed and done == set(nodes), "incomplete backward schedule")
    metrics = {"peak_bytes": peak, "recompute_cost": extra,
               "forward_cost": forward, "backward_cost": backward}
    return (metrics, trace) if with_trace else metrics


def verify(graph, certificate, expected_budget=None, with_trace=False):
    require(isinstance(certificate, dict), "certificate must be object")
    require(certificate.get("model") == MODEL, "wrong certificate model")
    require(certificate.get("graph_id") == graph.get("id"), "graph id mismatch")
    require(certificate.get("graph_sha256") == digest(graph), "graph hash mismatch")
    budget = certificate.get("budget")
    require(integer(budget), "invalid certificate budget")
    if expected_budget is not None:
        require(budget == expected_budget, "challenge budget mismatch")
    result = simulate(graph, certificate.get("actions"), budget, with_trace)
    metrics = result[0] if with_trace else result
    claims = certificate.get("claims")
    require(isinstance(claims, dict) and set(claims) == set(metrics), "missing/extra metric claim")
    require(all(integer(v) for v in claims.values()), "claims must be nonnegative integers")
    require(claims == metrics, f"incorrect claims: claimed {claims}, actual {metrics}")
    return result


def load(path):
    # Reject duplicate JSON keys instead of silently trusting the last occurrence.
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result
    p = Path(path)
    require(p.stat().st_size <= 64 * 1024 * 1024, "JSON file exceeds 64 MiB")
    return json.loads(p.read_text(), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(Invalid(f"invalid number {x}")))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("graph")
    p.add_argument("certificate")
    p.add_argument("--budget", type=int, required=True, help="challenge budget, not a candidate's choice")
    p.add_argument("--trace", action="store_true")
    args = p.parse_args()
    try:
        result = verify(load(args.graph), load(args.certificate), args.budget, args.trace)
    except (Invalid, OSError, ValueError, TypeError, KeyError) as error:
        p.exit(1, f"REJECT: {error}\n")
    print(json.dumps({"status": "PASS", "result": result}, sort_keys=True))


if __name__ == "__main__":
    main()
