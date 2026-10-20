# PyTorch comparison, separated from theoretical schedule records

Pinned experiment: torch 2.10.0, Python 3.12.8, CPU, float32, seed 20261020,
one thread, no training data or downloaded weights. `torch_probe.py` constructs
actual operations matching three workload shapes and checks every declared output
size. This is a behavior/gradient probe, not a device memory or speed benchmark.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r empirical/requirements.lock
.venv/bin/python torch_probe.py --out empirical/torch-cpu-rerun.json
```

Core verification does not need this environment. The default output path replaces
the local CPU evidence file; use `--out` to preserve it during a replication.
The initial environment is outside the repository in `../setup/torch-env/`.

| Graph | Mode | Forward macro attempts | Replay macro attempts | Replayed mm/bmm/conv dispatches | Hook-visible saved bytes |
|---|---|---:|---:|---:|---:|
| mlp-b4 | eager | 12 | 0 | 0 | 147456 |
| mlp-b4 | checkpoint-whole | 12 | 12 | 7 | 4096 |
| mlp-b4 | checkpoint-blocks | 12 | 12 | 4 | 16384 |
| mlp-b4 | selective | 12 | 12 | 0 | 4096 |
| mlp-b4 | checkpoint-sequential | 12 | 9 | 3 | 49152 |
| transformer-b2-t64 | eager | 28 | 0 | 0 | 2363392 |
| transformer-b2-t64 | checkpoint-whole | 28 | 27 | 15 | 65536 |
| transformer-b2-t64 | checkpoint-blocks | 28 | 26 | 14 | 131072 |
| transformer-b2-t64 | selective | 28 | 27 | 0 | 65536 |
| resnet-b2-c32 | eager | 10 | 0 | 0 | 1310720 |
| resnet-b2-c32 | checkpoint-whole | 10 | 10 | 4 | 262144 |
| resnet-b2-c32 | checkpoint-blocks | 10 | 10 | 4 | 524288 |
| resnet-b2-c32 | selective | 10 | 10 | 0 | 262144 |

All ten checkpoint variants matched eager outputs and all input/parameter gradients
within rtol=1e-4, atol=1e-5; observed maximum absolute gradient difference was zero.
Recomputation callbacks can be interrupted by non-reentrant early stopping; macro
attempts therefore differ from operations that reach the outer ATen dispatch mode.
ATen counts here include only calls inside forward/replay macros, not gradient
kernels. Selective checkpointing re-enters Python code but retrieves cached expensive
operator outputs; zero repeated expensive dispatches is expected for this policy.

**Hook-visible saved bytes are not peak memory.** These counts exclude parameters,
but omit SAC caches and other allocations. They measure unique storage seen by
saved-tensor hooks during forward before the scalar loss. Storage sharing is
counted once. They cannot establish that SAC uses as little memory as whole-region
checkpointing. Diagnostic single-run timings in JSON include first-use overhead and
are not speed-comparison evidence.

Theoretical counterparts are conceptual: eager saved activations; segment replay;
segment replay with the last segment retained (like checkpoint_sequential); and
save-expensive selective policies. The theoretical policies operate on declared
macro nodes, while PyTorch operates on actual autograd saved tensors and ATen ops.
The simulator's peaks must not be subtracted from PyTorch's hook counts. The
model uses reverse-ready backward ordering and excludes gradient/workspace memory;
this probe does not execute the optimized certificates as custom autograd programs.

`torch.compile` min-cut and memory-budget approaches are described by the
[PyTorch overview](https://pytorch.org/blog/activation-checkpointing-techniques/),
but are not measured here. API stability differs by PyTorch release; this probe
pins the actually exercised regional and selective APIs. See the
[checkpoint documentation](https://docs.pytorch.org/docs/stable/checkpoint) for
current semantics, and `requirements.lock` for this experiment's versions.

No GPU was used. Future validation first needs audited operator graphs and a
schedule executor with matching gradients, followed by separate controlled peak
allocated/reserved memory and runtime experiments. Theoretical frontier scores
must remain separate from those measurements.
