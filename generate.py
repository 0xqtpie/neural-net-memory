#!/usr/bin/env python3
"""Deterministically generate benchmark suite v1; no downloaded model weights."""
import argparse
import json
from pathlib import Path
from verifier import MODEL, digest, validate_graph

ROOT = Path(__file__).resolve().parent


def node(name, deps, size, cost=1, req=None, kind="synthetic", recomputable=True):
    return {"id": name, "deps": deps, "bytes": size, "cost": cost,
            "backward_cost": 2 * cost, "backward_requires": deps if req is None else req,
            "recomputable": recomputable, "kind": kind}


def graph(name, nodes, input_bytes, family, provenance):
    used = {d for n in nodes for d in n["deps"]}
    g = {"model": MODEL, "id": name, "inputs": [{"id": "x", "bytes": input_bytes}],
         "nodes": nodes, "outputs": [n["id"] for n in nodes if n["id"] not in used],
         "family": family, "provenance": provenance,
         "cost_unit": "integer abstract forward work; not elapsed time"}
    return validate_graph(g)


def synthetic():
    result = []
    for name, sizes, costs in [
        ("chain6-unit", [1] * 6, [1] * 6),
        ("chain6-weighted", [3, 8, 2, 7, 2, 1], [1, 3, 1, 2, 1, 1]),
    ]:
        ns = [node(f"n{i}", ["x" if i == 0 else f"n{i-1}"], s, costs[i])
              for i, s in enumerate(sizes)]
        result.append(graph(name, ns, 1, "synthetic", {"source": "hand-defined exact test family"}))
    result.append(graph("diamond5", [
        node("a", ["x"], 2), node("b", ["a"], 5, 2),
        node("c", ["a"], 3), node("d", ["b", "c"], 2, 2),
        node("e", ["d"], 1)], 1, "synthetic", {"source": "fork-join exact test"}))
    result.append(graph("skip6", [
        node("a", ["x"], 3), node("b", ["a"], 6), node("c", ["b"], 2, 2),
        node("d", ["a", "c"], 3, req=[]), node("e", ["d"], 5, 2),
        node("f", ["a", "e"], 1, req=[])], 2, "synthetic",
        {"source": "residual-like exact test"}))
    result.append(graph("stateful4", [
        node("a", ["x"], 2, recomputable=False),
        node("b", ["a"], 4), node("c", ["b"], 2),
        node("d", ["a", "c"], 1)], 1, "synthetic",
        {"source": "non-recomputable operation control; not a random-number model"}))
    return result


def transformer(blocks, tokens):
    batch, dim, heads, ff = 2, 128, 4, 512
    a, s, f = batch * tokens * dim, batch * heads * tokens * tokens, batch * tokens * ff
    ns = []
    prev = "x"
    for block in range(blocks):
        prefix = f"b{block}_"
        def add(suffix, deps, elements, cost, kind, req=None):
            name = prefix + suffix
            ns.append(node(name, deps, 4 * elements, cost, req, kind))
            return name
        norm = add("norm1", [prev], a, 5 * a, "norm")
        q = add("q", [norm], a, 2 * a * dim, "linear")
        k = add("k", [norm], a, 2 * a * dim, "linear")
        v = add("v", [norm], a, 2 * a * dim, "linear")
        scores = add("scores", [q, k], s, 2 * s * (dim // heads), "matmul")
        probs_name = prefix + "probs"
        probs = add("probs", [scores], s, 5 * s, "softmax", [probs_name])
        context = add("context", [probs, v], a, 2 * s * (dim // heads), "matmul")
        proj = add("proj", [context], a, 2 * a * dim, "linear")
        residual = add("residual1", [prev, proj], a, a, "add", [])
        norm2 = add("norm2", [residual], a, 5 * a, "norm")
        up = add("up", [norm2], f, 2 * a * ff, "linear")
        act = add("gelu", [up], f, 8 * f, "gelu")
        down = add("down", [act], a, 2 * f * dim, "linear")
        prev = add("residual2", [residual, down], a, a, "add", [])
    return graph(f"transformer-b{blocks}-t{tokens}", ns, 4 * a, "transformer", {
        "source": "https://arxiv.org/abs/1706.03762",
        "derivation": "hand-derived pre-norm residual attention/MLP block; unfused dense attention",
        "batch": batch, "tokens": tokens, "width": dim, "heads": heads, "ff": ff,
        "dtype_bytes": 4, "blocks": blocks,
        "limitations": "No dropout, masks, positional encoding, fused kernels, views, or persistent norm statistics. Macro-op scratch excluded; costs analytic proxies."
    })


def residual_cnn(blocks, channels=32, side=32):
    batch = 2
    elements = batch * channels * side * side
    ns, prev = [], "x"
    for i in range(blocks):
        conv1, relu, conv2, add, out = [f"b{i}_{s}" for s in ("conv1", "relu1", "conv2", "add", "relu2")]
        ns.extend([
            node(conv1, [prev], 4 * elements, 2 * elements * channels * 9, kind="conv"),
            node(relu, [conv1], 4 * elements, elements, req=[relu], kind="relu"),
            node(conv2, [relu], 4 * elements, 2 * elements * channels * 9, kind="conv"),
            node(add, [prev, conv2], 4 * elements, elements, req=[], kind="add"),
            node(out, [add], 4 * elements, elements, req=[out], kind="relu")
        ])
        prev = out
    return graph(f"resnet-b{blocks}-c{channels}", ns, 4 * elements, "convolution", {
        "source": "https://arxiv.org/abs/1512.03385",
        "derivation": "hand-derived residual conv/ReLU block, stride one, padding one; batch norm omitted",
        "batch": batch, "channels": channels, "height": side, "width": side,
        "kernel": 3, "dtype_bytes": 4, "blocks": blocks,
        "limitations": "Not a traced full ResNet; convolution workspace and parameter/gradient allocations excluded."
    })


def mlp(layers):
    batch, dim, hidden = 8, 128, 512
    ns, prev = [], "x"
    for i in range(layers):
        up, act, down = [f"b{i}_{s}" for s in ("up", "gelu", "down")]
        ns.extend([
            node(up, [prev], batch * hidden * 4, 2 * batch * dim * hidden, kind="linear"),
            node(act, [up], batch * hidden * 4, 8 * batch * hidden, kind="gelu"),
            node(down, [act], batch * dim * 4, 2 * batch * hidden * dim, kind="linear")
        ])
        prev = down
    return graph(f"mlp-b{layers}", ns, batch * dim * 4, "mlp",
                 {"source": "standard dense/GELU/dense stack", "batch": batch,
                  "width": dim, "hidden": hidden, "blocks": layers, "dtype_bytes": 4,
                  "derivation": "analytic operator graph, no tracing or measured costs"})


def suite():
    graphs = synthetic() + [transformer(1, 32), transformer(2, 64), transformer(4, 128),
                            residual_cnn(2), residual_cnn(4), mlp(4), mlp(8)]
    entries = []
    for g in graphs:
        total = sum(n["cost"] for n in g["nodes"])
        budgets = sorted({0, total // 4, total // 2, total, 2 * total})
        entries.append({"id": g["id"], "path": f"benchmarks/graphs/{g['id']}.json",
                        "sha256": digest(g), "budgets": budgets,
                        "exact": g["family"] == "synthetic", "family": g["family"]})
    manifest = {"suite": "activation-memory-benchmarks/v1", "model": MODEL,
                "seed": None, "generation": "fully deterministic; no random graph draws",
                "graphs": entries}
    return graphs, manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    graphs, manifest = suite()
    files = {entry["path"]: g for entry, g in zip(manifest["graphs"], graphs)}
    files["benchmarks/suite.json"] = manifest
    for rel, value in files.items():
        path = ROOT / rel
        content = json.dumps(value, indent=2) + "\n"
        if args.check:
            assert path.read_text() == content, f"frozen benchmark drift: {rel}"
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print(f"PASS: {len(graphs)} deterministic graphs; {sum(len(e['budgets']) for e in manifest['graphs'])} challenges")


if __name__ == "__main__":
    main()
