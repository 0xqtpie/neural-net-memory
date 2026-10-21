# Executed workload and compatible solver audit — 21 October 2026

One executed PyTorch residual feed-forward block now has an audited fixed-shape
export. OR-Tools CP-SAT and the existing exhaustive solver agree on all 18
comparison cases. The exported block is already solved: **18,432 modeled bytes**
at additional-forward budgets 0, 2 and 4. Use it as a fidelity control, not as an
open donor challenge. This does not establish GPU memory savings or optimizer
superiority over production checkpointing systems.

## Workload evidence

`export_workload.py` executes a bias-free 64→256→64 residual feed-forward block,
with ReLU after the expansion and residual addition, batch 8, float32 CPU,
seed 20261021, one thread, PyTorch 2.10.0. `fx-graph.txt` and `aten-graph.txt`
retain the actual traces; `graph.json` is a separately identified v1 fixture.
The original 12 graphs and 60 challenge rows remain frozen.

| Allocation | Output bytes | Saved activations needed for backward |
|---|---:|---|
| Immutable input x | 2,048 | Always live in this model |
| Expansion linear | 8,192 | x |
| First ReLU | 8,192 | Its own output |
| Projection linear | 2,048 | First ReLU output |
| Residual addition | 2,048 | None |
| Final ReLU | 2,048 | Its own output |

The audit checks distinct contiguous output storage, strides, offsets, storage
sizes, and every saved tensor against either an activation or a parameter.
Unknown saved storage fails the export. Matrix-calculus gradients are checked
against autograd, and saved-tensor hooks preserve the ordinary autograd gradients.
The hand-derived backward requirements match the observed saved activations.
Parameters consume 131,072 bytes and are explicitly outside the model.

The unavoidable allocation of the first ReLU while its input and immutable x
remain live gives 2,048 + 8,192 + 8,192 = 18,432 bytes. A verified schedule attains
that bound without recomputation. Additional compute cannot improve this fixture.
This is a small real executed network block, not a production model suite. Linear
is an operator boundary; intra-operator workspaces, gradients and backward
allocations remain excluded by activation-memory/v1. The abstract optimized
schedule has **not** been executed by autograd. Hook-visible tensors are not total
training memory.

## Solver comparison

The new adapter uses [OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver),
version 9.15.6755, one worker, seed 20261021, 15 seconds per comparison case.
`solver-requirements.lock` pins its separate environment. This is our formulation
on a mature solver, not an execution or reproduction of Checkmate, DTR or Moccasin.
A native-system comparison remains separate work and requires a documented
semantic bridge.

At each time step the encoding permits one forward, drop, backward or loss
operation, or no-op, with independent live/seen/done/phase variables. It enforces
all dependencies, non-recomputable nodes, the loss barrier, allocation before
freeing and the exact weighted recomputation budget. There is no imposed fixed
forward order. If k=floor(budget/min_forward_cost), at most n+k forwards, n+k
drops, n backwards and one loss are useful: H=3n+2k+1 is a complete horizon.
OPTIMAL thus concerns the full declared model, not a truncated schedule horizon.
The adapter refuses horizons above 120; timed-out solves never acquire an
optimality claim.

`solver-results.json` retains all 18 runs: five existing synthetic DAGs and the
new export at budgets 0, 2 and 4. Every case was OPTIMAL, matched independent
state-space enumeration, and produced a certificate accepted by the standalone
verifier. Two synthetic cases beat the best enumerated checkpoint/segment
baseline, but these optima were already known and are not new discoveries.
Additional seeded differential tests cover multiple sinks, empty requirements,
non-recomputable operations, weighted budgets and resource-cap rejection.
Wall times are descriptive; this is not a controlled speed benchmark.

## Reproduction and decision

Fast evidence replay needs only the standard library:

```sh
python3 research/scientific-audit-20261021/verify_evidence.py
```

To rerun the exporter and solver comparison, from the repository root:

```sh
# Existing empirical PyTorch environment, or a separate environment using empirical/requirements.lock
/path/to/torch-python research/scientific-audit-20261021/export_workload.py
uv venv --python 3.12 scratch/scientific-audit/solver-env
uv pip install --python scratch/scientific-audit/solver-env/bin/python -r research/scientific-audit-20261021/solver-requirements.lock
scratch/scientific-audit/solver-env/bin/python research/scientific-audit-20261021/cpsat_compare.py
scratch/scientific-audit/solver-env/bin/python -m unittest discover -s research/scientific-audit-20261021 -p 'test_*.py' -v
python3 verify_all.py
```

Evidence is coordinator/author-checked; independent scientific review remains
pending. Keep the exported block as an audit control. Before promoting a new
training graph to active search, demonstrate a nontrivial rematerialization gap,
repeat the saved-storage audit, and compare the same constraints against a mature
solver. Normalization statistics and view/alias semantics still need separate
coverage before admitting transformer training exports.
