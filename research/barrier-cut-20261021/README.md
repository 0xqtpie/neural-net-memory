# A stronger memory floor for transformer-b4-t128

**Author-checked bound proposal:** every legal schedule for the unchanged
`transformer-b4-t128` graph needs at least **1,310,720 activation bytes**, at every
recomputation budget. This raises three working lower bounds from 1,179,648.
It does not improve any fixed-budget schedule or settle the selected row.
The selected budget 956,301,312 now has the proposed interval
**[1,310,720, 1,441,792]**, halving the previous 262,144-byte gap.
Existing graphs, model semantics, certificates and records are unchanged.

| Additional-forward budget | Working lower bound | Proposed bound | Existing witness |
|---:|---:|---:|---:|
| 239,075,328 | 1,179,648 | 1,310,720 | 2,883,584 |
| 478,150,656 | 1,179,648 | 1,310,720 | 1,835,008 |
| 956,301,312 (selected) | 1,179,648 | 1,310,720 | 1,441,792 |

The bound is weaker than the existing bounds at budgets 0 and 119,537,664;
those rows have no proposed change. This package proposes results for review;
it does not update the project's record of accepted results.

## Proof

Let `u = 131,072` bytes. The immutable input `x` occupies `u`.
In the first block, `scores`, `probs`, `up`, and `gelu` each occupy `4u`.
Forward outputs allocate before any input can be dropped (MODEL.md).
Consequently, under a hypothetical peak cap `9u`, executing either `probs`
or `gelu` forces the **entire** live set to be exactly:

- `probs`: `{x, b0_scores, b0_probs}`;
- `gelu`: `{x, b0_up, b0_gelu}`.

Both events are strict ancestors of the mandatory `b0_residual2` forward.
Consider the **last** of these two events before `b0_residual2` first executes.
There must be such an event, regardless of execution ordering or replay count.

If it is `probs`, no GELU output is live. Without another GELU execution,
`b0_down` cannot be produced. If it is `gelu`, no attention result is live.
Without another `probs` execution, `b0_context`, `b0_proj`, and
`b0_residual1` cannot be produced. In either case `b0_residual2` cannot acquire
both of its inputs. This contradicts the choice of the last event.

Thus peak `9u` is impossible, even with unlimited recomputation. Every allocation
is an integer multiple of `u`, so the next possible peak is `10u = 1,310,720`.
Backward or budget constraints cannot weaken this forward-only obstruction.

`reset_cut.py` generalizes the argument: find mandatory ancestor events whose
local input/output allocation saturates a candidate cap. For each possible last
event, compute the unrestricted forward closure of its forced live set while
forbidding all events in the set. Failure to reach a mandatory target for **every**
last event certifies the cut. The closure relaxes all other memory, work and
non-recomputability constraints, so it over-approximates legal continuations.
`cut.json` records the exact live sets, closures, graph hash and allocation quantum.
The checker validates these premises; it does not trust a stored bound alone.
This is a mathematical argument with executable checks, not a machine-checked proof
or independently reviewed result.

## Replay

From the repository root, using Python 3.9+ and the standard library:

```sh
python3 research/barrier-cut-20261021/verify_result.py
python3 -m unittest discover -s research/barrier-cut-20261021 -p 'test_*.py' -v
python3 research/barrier-cut-20261021/reset_cut.py benchmarks/graphs/transformer-b4-t128.json --check research/barrier-cut-20261021/cut.json
python3 verify_all.py
```

Controls include the 25 fixed tiny rows; an exact six-node residual example
with optimum 10 and a no-join example with optimum 9; invalid-bound, missing-barrier,
nonancestor, stale-hash and boolean-cap rejection; and 146 small forward-only
DAG cases checked by a separately written exhaustive minimax enumerator.
The cut applies in 26 of those 146 cases and never exceeds their forward optima.
That enumerator relaxes backward and work budgets and is stronger validation of a
forward-only obstruction than comparison solely to backward-constrained optima.
All checks remain author checks, including the separately written enumerator.

## Construction attempts and favorable pricing

Before search, the favorable fully charged relaxation included all first-forward
work (478,150,656), fixed backward work (956,301,312, outside the extra-forward
budget), immutable input, loss sink and output-before-input-free transients.
At a 10u loss cap, retaining the most own-forward work in the remaining bytes
still forces at least 209,682,432 extra work units after loss. This favorable
floor relaxes dependency and repeated replays; it did not rule out the target.
It was never a construction or a guarantee of attainable cost.

An offline beam prototype branched over retained-value states, dependency order
and minimal sufficient eviction sets, with a fixed topological first-forward
order and reverse backward order. At cap 10u and the drawn budget, widths
128/16 and 1024/64 both exhausted retained labels during block-2 backward.
These truncated searches do **not** prove infeasibility. A cap-11u control with
widths 128/16 hit its 45-second limit despite an already known legal witness;
this is an explicit limitation of the prototype, which is not shipped as a solver.
The existing 11u witness itself was successfully replayed with the project verifier.
Search limits are wall-time safeguards, not controlled performance comparisons.

**Auxiliary challenge outside the fixed suite:** relaxing the budget for a diagnostic
run produced a 10u witness costing **1,258,192,896** extra work units. It is stored
in `certificates/auxiliary-budget.json` with its actual cost as its declared budget.
It misses the selected budget by **301,891,584** and is **not an improvement on any
fixed suite row**. It does demonstrate that the memory floor can be attained with
more compute. Replaying its explicit actions, rather than reconstructing the
heuristic's trajectory, is this auxiliary witness's reproduction contract.
The failed-search prototype and raw session logs remain in the donor's local
session evidence; `TASK.json` records parameters and outcomes.

## Open next questions

- Can a 10u schedule reduce the auxiliary extra cost by 301,891,584 to meet the
  selected 956,301,312 budget? Start with the auxiliary action trace and identify
  repeated prefix regenerations; preserve the exact graph and allocation rules.
- Alternatively, can a budget-sensitive cut prove that 10u is impossible at the
  selected budget, matching the existing 11u witness? Truncated beam failure is
  insufficient; a complete relaxation or auditable exact argument is required.
- Independently review the last-event argument and the closure check before
  promoting the proposed bounds.

## Provenance and credit

Base: `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`.
Seed: `dafc4be0863b7654352ffb2ba4a4d2df`.
The original project picker drew model fidelity; after the donor clarified the
numerical-frontier priority, a documented restriction to the two numerical tracks
selected this graph/budget with the same seed. This is an explicit scope change,
not an output of the unmodified picker. Details are in `TASK.json`.

Work by the donor's Codex AI agent for @0xqtpie. Credit Doug Colkitt
(@Mister-Meeseeks), the project's model and standalone verifier, the trial's stronger
working schedules and local/knapsack/zero-budget bounds, and its 4,000-attempt
failed focused cache campaign. The trial's 11u witness supplies the upper bound
used here. `SOURCES.json` pins these predecessors. Pebbling and rematerialization
have extensive prior art, including Checkmate and Moccasin; this package claims a
new checked result for this project's graph, not a new optimization problem or
general state of the art. No GPU, total training-memory, or runtime-saving claim.
