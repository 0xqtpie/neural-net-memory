#!/usr/bin/env python3
"""Check the square-root segmentation scaling on uniform linear chains."""
import json
import math
import argparse
from pathlib import Path
from generate import graph, node
from search import certificate, checkpoint_schedule


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows = []
    for length in [16, 64, 256]:
        ns = [node(f"n{i}", ["x" if i == 0 else f"n{i-1}"], 1) for i in range(length)]
        g = graph(f"replication-chain{length}", ns, 1, "replication", {})
        width = math.isqrt(length)
        ids = [n["id"] for n in ns]
        groups = [ids[i:i + width] for i in range(0, length, width)]
        actions = checkpoint_schedule(g, set(), groups)
        c = certificate(g, actions, length, "square-root-segments")
        # Finite-instance checks of the standard construction; no asymptotic proof
        # is inferred from a curve. Each unit is a byte in this synthetic model.
        assert c["claims"]["peak_bytes"] <= 2 * width + 2
        assert c["claims"]["recompute_cost"] <= length
        rows.append({"length": length, "width": width, **c["claims"],
                     "eager_peak_bytes": length + 1})
    path = Path(__file__).resolve().parent / "records/chain-replication.json"
    content = json.dumps({
        "source": "https://arxiv.org/abs/1604.06174",
        "scope": "uniform-chain segment construction in activation-memory/v1; not the paper's hardware experiments",
        "rows": rows}, indent=2) + "\n"
    if args.check:
        assert path.read_text() == content, "chain replication record drift"
    else:
        path.write_text(content)
    print("PASS: square-root segmentation on lengths 16, 64, 256")


if __name__ == "__main__":
    main()
