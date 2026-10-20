#!/usr/bin/env python3
"""Optional real PyTorch CPU checkpoint behavior/gradient probe, NOT a GPU benchmark.

Runs the exact tensor shapes of three workload graph definitions. Hook-visible saved
storage is an incomplete diagnostic (especially for SAC), never peak device memory.
"""
import argparse
from collections import Counter
from functools import partial
import json
from pathlib import Path
import platform
import time

import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.checkpoint import (
    checkpoint, checkpoint_sequential, create_selective_checkpoint_contexts, CheckpointPolicy)
from torch.utils._python_dispatch import TorchDispatchMode
from verifier import load

ROOT = Path(__file__).resolve().parent


class Workload(nn.Module):
    def __init__(self, graph):
        super().__init__()
        self.graph = graph
        self.nodes = {n["id"]: n for n in graph["nodes"]}
        self.weights = nn.ParameterDict()
        self.counts = Counter()
        self.in_macro = False
        self.sizes = {n["id"]: n["bytes"] for n in graph["inputs"] + graph["nodes"]}
        p = graph["provenance"]
        if graph["family"] == "transformer":
            self.shape = (p["batch"], p["tokens"], p["width"])
            leading = p["batch"] * p["tokens"]
        elif graph["family"] == "convolution":
            self.shape = (p["batch"], p["channels"], p["height"], p["width"])
            leading = None
        else:
            self.shape = (p["batch"], p["width"])
            leading = p["batch"]
        for n in graph["nodes"]:
            if n["kind"] == "linear":
                incoming = self.sizes[n["deps"][0]] // 4 // leading
                outgoing = n["bytes"] // 4 // leading
                self.weights[n["id"]] = nn.Parameter(torch.randn(outgoing, incoming) / incoming ** .5)
            elif n["kind"] == "conv":
                c = p["channels"]
                self.weights[n["id"]] = nn.Parameter(torch.randn(c, c, 3, 3) / (9 * c) ** .5)

    def op(self, node, env):
        self.in_macro = True
        try:
            return self._op(node, env)
        finally:
            self.in_macro = False

    def _op(self, node, env):
        name, kind = node["id"], node["kind"]
        args = [env[d] for d in node["deps"]]
        self.counts[name] += 1  # attempted macro-op invocations; early-stop may interrupt
        if kind == "linear":
            out = F.linear(args[0], self.weights[name])
        elif kind == "conv":
            out = F.conv2d(args[0], self.weights[name], padding=1)
        elif kind == "norm":
            out = F.layer_norm(args[0], (args[0].shape[-1],))
        elif kind == "gelu":
            out = F.gelu(args[0])
        elif kind == "relu":
            out = F.relu(args[0])
        elif kind == "softmax":
            out = torch.softmax(args[0], -1)
        elif kind == "add":
            out = args[0] + args[1]
        elif kind == "matmul":
            batch, tokens, dim = self.shape
            heads = self.graph["provenance"]["heads"]
            def split(x):
                return x.reshape(batch, tokens, heads, dim // heads).transpose(1, 2)
            if name.endswith("scores"):
                out = (split(args[0]) @ split(args[1]).transpose(-1, -2)) / (dim // heads) ** .5
            else:
                out = (args[0] @ split(args[1])).transpose(1, 2).contiguous().reshape(batch, tokens, dim)
        else:
            raise ValueError(kind)
        assert out.numel() * out.element_size() == node["bytes"], name
        return out

    def region(self, ids, incoming, outgoing):
        def run(*args):
            env = dict(zip(incoming, args))
            for i, name in enumerate(ids):
                env[name] = self.op(self.nodes[name], env)
                needed = set(outgoing) | {d for later in ids[i + 1:] for d in self.nodes[later]["deps"]}
                env = {k: v for k, v in env.items() if k in needed}
            return tuple(env[n] for n in outgoing)
        return run

    def execute(self, x, mode):
        ids = list(self.nodes)
        if mode in {"eager", "checkpoint-whole", "selective"}:
            groups = [ids]
        else:
            groups = []
            for name in ids:
                if not groups or name.split("_")[0] != groups[-1][0].split("_")[0]:
                    groups.append([])
                groups[-1].append(name)
        if mode == "checkpoint-sequential":
            assert self.graph["family"] == "mlp"
            functions = []
            for group in groups:
                incoming = [self.nodes[group[0]]["deps"][0]]
                run = self.region(group, incoming, [group[-1]])
                functions.append(lambda value, fn=run: fn(value)[0])
            return checkpoint_sequential(functions, len(functions), x, use_reentrant=False)
        env = {"x": x}
        for group in groups:
            own = set(group)
            incoming = sorted({d for n in group for d in self.nodes[n]["deps"] if d not in own})
            # All values that cross a region boundary plus final outputs.
            outgoing = sorted(own & (set(self.graph["outputs"]) | {
                d for n in ids if n not in own for d in self.nodes[n]["deps"]}))
            fn = self.region(group, incoming, outgoing)
            args = [env[n] for n in incoming]
            if mode == "eager":
                outputs = fn(*args)
            elif mode == "selective":
                save_ops = {torch.ops.aten.mm.default, torch.ops.aten.bmm.default,
                            torch.ops.aten.addmm.default, torch.ops.aten.convolution.default}
                def policy(ctx, op, *args, **kwargs):
                    return CheckpointPolicy.MUST_SAVE if op in save_ops else CheckpointPolicy.PREFER_RECOMPUTE
                outputs = checkpoint(fn, *args, use_reentrant=False,
                                     context_fn=partial(create_selective_checkpoint_contexts, policy))
            else:
                outputs = checkpoint(fn, *args, use_reentrant=False)
            env.update(zip(outgoing, outputs))
            remaining = ids[ids.index(group[-1]) + 1:]
            needed = set(self.graph["outputs"]) | {d for n in remaining for d in self.nodes[n]["deps"]}
            env = {k: v for k, v in env.items() if k in needed}
        return env[self.graph["outputs"][0]]


def run_one(model, inp, mode):
    model.zero_grad(set_to_none=True)
    model.counts.clear()
    x = inp.detach().clone().requires_grad_(True)
    parameter_ptrs = {p.untyped_storage().data_ptr() for p in model.parameters()}
    packed = {}
    phase = "forward"
    dispatched = {"forward": Counter(), "replay": Counter()}
    class CountDispatch(TorchDispatchMode):
        def __torch_dispatch__(self, func, types, args=(), kwargs=None):
            if model.in_macro:
                dispatched[phase][str(func)] += 1
            return func(*args, **(kwargs or {}))
    def pack(t):
        storage = t.untyped_storage()
        if storage.data_ptr() not in parameter_ptrs and storage.nbytes():
            packed[(storage.data_ptr(), storage.nbytes())] = storage.nbytes()
        return t
    started = time.perf_counter()
    with CountDispatch(), torch.autograd.graph.saved_tensors_hooks(pack, lambda t: t):
        out = model.execute(x, mode)
        before = dict(model.counts)
        saved_bytes = sum(packed.values())
        phase = "replay"
        loss = out.square().mean()
        loss.backward()
    grads = [x.grad.detach().clone()] + [p.grad.detach().clone() for p in model.parameters()]
    record = {"mode": mode, "loss": loss.item(),
              "forward_macro_invocations": sum(before.values()),
              "backward_replay_macro_attempts": sum(model.counts.values()) - sum(before.values()),
              "hook_visible_nonparameter_unique_storage_bytes_forward": saved_bytes,
              "forward_macro_aten_dispatch": dict(dispatched["forward"]),
              "replay_macro_aten_dispatch": dict(dispatched["replay"]),
              "seconds_diagnostic_only": time.perf_counter() - started}
    return record, grads, out.detach().clone()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="empirical/torch-cpu.json")
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.manual_seed(20261020)
    results = []
    for name in ["mlp-b4", "transformer-b2-t64", "resnet-b2-c32"]:
        graph = load(ROOT / f"benchmarks/graphs/{name}.json")
        model = Workload(graph)
        inp = torch.randn(model.shape)
        reference, gradients, output = run_one(model, inp, "eager")
        results.append({"graph": name, **reference, "gradient_check": "reference"})
        modes = ["checkpoint-whole", "checkpoint-blocks", "selective"]
        if graph["family"] == "mlp":
            modes += ["checkpoint-sequential"]
        for mode in modes:
            record, candidate, actual_output = run_one(model, inp, mode)
            torch.testing.assert_close(actual_output, output, rtol=1e-4, atol=1e-5)
            for a, b in zip(candidate, gradients):
                torch.testing.assert_close(a, b, rtol=1e-4, atol=1e-5)
            results.append({"graph": name, **record, "gradient_check": "PASS",
                            "max_absolute_gradient_difference": max(
                                (a-b).abs().max().item() for a, b in zip(candidate, gradients))})
    report = {
        "kind": "empirical CPU behavior and gradient validation; no GPU peak-memory claim",
        "environment": {"torch": torch.__version__, "python": platform.python_version(),
                        "platform": platform.platform(), "device": "cpu", "threads": 1,
                        "seed": 20261020, "dtype": "float32"},
        "limitations": [
            "Saved-tensor hooks omit SAC caches and other allocations; these bytes are not total or peak memory.",
            "Replay counts are macro-op attempts, not weighted model costs or complete ATen execution counts.",
            "ATen dispatch counts cover calls inside graph forward/replay macros; backward gradient kernels are excluded.",
            "Model graphs omit views, normalization statistics, gradient buffers and scratch.",
            "Single diagnostic timings are not controlled speed benchmarks.",
            "torch.compile/min-cut/budget APIs documented but not measured here.",
            "No optimized certificate was executed as a custom PyTorch autograd schedule."
        ],
        "results": results
    }
    path = ROOT / args.out
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {len(results)} CPU configurations; all checkpoint gradients agree with eager")


if __name__ == "__main__":
    main()
