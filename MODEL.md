# Activation memory model v1

The normative model identifier is `activation-memory/v1`. The normative checker is
`verifier.py`; changing semantics requires a new model/suite version and replay.
All sizes, costs, budgets, claims, and memory arithmetic are nonnegative integers;
tensor sizes and operation costs are strictly positive. Booleans are not integers.

## Graph and backward semantics

A graph has immutable external inputs, operations in a topologically sorted list,
and exactly its sink nodes as outputs. Each operation produces one distinct,
contiguous logical tensor. `deps` lists every forward activation dependency.
`bytes` is its allocation size. `cost` is the work of one forward execution.
`backward_requires` explicitly lists saved values needed by its backward, drawn from
the node itself and its ancestors. It may be empty. `backward_cost` is fixed work for
that backward. `recomputable=false` prohibits a second forward execution.

The operation list is a serialization order, not a restriction on execution order.
Any dependency-ready operation can execute. Every operation must execute at least
once before the loss barrier. All sink outputs must coexist at that barrier, which
seeds all sink gradients (conceptually the sum of losses over the sinks). Backward
executes each operation exactly once, after every forward consumer's backward is
finished. Its declared saved values must be live. Gradient contributions are assumed
available/accumulated according to that order; their allocations are excluded below.
The backward never creates or regenerates a forward activation.

Graph nodes describe deterministic pure operations on fixed inputs and parameters.
There is no dropout or mutable parameter update. A non-recomputable node is a control
for operations that cannot safely be repeated; this is not a full RNG-state model.
Real operations must be expanded or annotated correctly before importing a graph.
The verifier checks the declared model, not the truth of a model exporter.

## Allowed actions

| Action | Preconditions | Effect |
|---|---|---|
| `forward(v)` | Output absent, all `deps` live; repeat allowed only if recomputable | Allocate output; first call marks node evaluated; subsequent calls spend `cost` from recomputation budget |
| `drop(v)` | Internal tensor live | Free its allocation; does not erase execution history |
| `loss` | All nodes evaluated, every sink live, not already sealed | Seed backward; no activation allocation |
| `backward(v)` | Loss sealed, all consumers' backwards done, required activations live, not already done | Mark backward complete; no activation allocation |
| retain | No action needed | Tensor stays resident until an explicit drop |

External inputs remain live throughout and cannot be freed or regenerated. There is
no overwrite of a live tensor, offload, compression, aliasing, in-place reuse, fusion,
parallel execution, or partial recomputation. Forward regeneration can occur both
before and after the loss barrier. Tensor names refer to the same deterministic
value on every regeneration. A complete certificate need not free its final live
tensors, but must finish every backward.

## Memory and objective

If `L` is the resident tensor set, memory is `sum(bytes[v] for v in L)`.
**A forward output is allocated while all inputs and all other retained values are
still live.** Inputs cannot be freed atomically with execution. The peak includes
the initial external input allocation and every intermediate action boundary.
For example, a 5-byte input and 7-byte output require a peak of at least 12 bytes,
even if the output is immediately discarded. The loss barrier counts every sink.

The objective for challenge `(graph hash, B)` is to minimize this peak subject to
`sum(cost[v] for every forward(v) after its first) <= B`. Baseline first-forward
cost is `sum(cost)` and total forward cost is that plus recomputation.
Backward cost is the fixed `sum(backward_cost)`; all nodes' backwards are mandatory.
Backward work is not charged to the *additional forward recomputation* budget.
Ties in peak are not research improvements, even if the search uses cost to break ties.

Excluded: parameter tensors and their gradients, activation gradients and gradient
accumulation buffers, optimizer state, scalar loss/seed, host scheduling metadata,
allocator rounding/fragmentation/caching, kernel workspaces, and intra-operation
temporaries. Normalization statistics, attention reshaping/copies, and similar
implementation details inside workload macro-ops are outside this abstraction.
There is no claim that these excluded allocations are small on real hardware.
All **declared** forward input/output allocations are included. Sizes of external
inputs are counted, not silently hidden in a free-input convention.

## Workload provenance and costs

The seven workload-derived graphs are analytic, shape-parameterized MLP, pre-norm
transformer, and residual convolution blocks. They are not exported full production
models. `generate.py` fixes shapes, formulas, dependencies, saved requirements and
costs; JSON provenance names omissions. Float32 sizes use four bytes per element.
Dense layers use `2 * batch_elements * input_width * output_width`, convolution
uses `2 * output_elements * input_channels * kernel_area`; pointwise and normalization
costs use stated integer multiples. These are work proxies, not measured latency.
For a transformer score node the scalar scaling is subsumed in the macro-op;
backward costs of twice forward cost are bookkeeping proxies, not FLOP claims.

`torch_probe.py` instantiates matching shapes and forward operations for three
representatives, asserts each macro output's size, and checks checkpoint gradients.
This supports graph plausibility but does not validate every saved-tensor assumption
or execute the optimized certificates on a GPU.

## Certificates and exact search

Certificate fields: model, graph ID, SHA-256 of canonical graph JSON (sorted keys,
ASCII JSON, compact separators), challenge budget, explicit action list, and exact
claims for peak bytes, recomputation cost, forward cost, and backward cost.
`method` and `metadata` describe provenance; they do not establish optimality.
The verifier takes the budget from the challenge separately to prevent substitution.
Duplicate JSON keys, noninteger claims and hash mismatches are rejected.

The exact solver is minimax Dijkstra on states `(live, seen, backward_done,
loss_sealed, spent)`. Immutable inputs are implicit in `live`. The remaining sets
are finite bit masks and `spent` is in `[0,B]`. Its transitions enumerate every
legal forward, drop, backward and loss action. The path score is the maximum live
memory so far; each transition takes `max(previous_score, target_memory)`.
Forward allocation is represented before any later drop, so this captures transient
input/output coexistence. States with the same components and a larger peak are
dominated. Thus the first removed goal state has minimum peak in this finite model.
This is a mathematical argument implemented and tested, not a machine-checked proof.
Re-running search, not merely verifying its witness, checks its optimum claim.
A resource cap raises an error and cannot produce an optimality claim.

For larger cases a valid lower bound is the largest mandatory local allocation:
fixed inputs plus an operation's distinct input/output tensors, or fixed inputs
plus a backward's required values, or fixed inputs plus all sinks. Matching this
bound proves optimality in the model. Otherwise the row remains open; a gap can
reflect a weak bound rather than an attainable improvement.

The implementation also uses a budget-sensitive loss-barrier bound. Let `R` be all
values required by any backward, and `F` the external inputs and sinks that must
be live at loss. A value in `R-F` absent at loss must be recomputed at least once
after loss, spending at least its own forward cost. Non-recomputable values cannot
be absent. Relaxing away dependency/replay constraints, solve a 0/1 knapsack that
maximizes discarded bytes subject to summed cost at most B. Then
`bytes(F union R) - maximum_discarded_bytes` is a valid lower bound on loss memory.
The reported larger-case bound is the maximum of this bound and the local bound.
At B=0 it counts every backward-required value at loss. The exact knapsack DP maps
saved bytes to minimum cost; if it exceeds 100,000 states, it returns only the local
bound. This fallback weakens a bound and never claims a truncated knapsack optimum.
