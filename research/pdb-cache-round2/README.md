# Less replay work at the existing b4 transformer peak

For the frozen `transformer-b4-t128` case with additional-forward budget
956,301,312, a new full schedule reduces additional forward work from
**737,935,360 to 702,349,312** at the existing **1,441,792-byte peak**.
The reduction is 35,586,048 work units, or **4.82%**. This is a secondary
work improvement at a fixed peak, not a new peak result or a global work optimum.
The unchanged full verifier checks every allocation and every repeated forward.

## Constructor and replay

From the repository root, standard-library Python 3.9 or later:

```sh
python3 research/pdb-cache-round2/replay.py
python3 -m unittest discover -s research/pdb-cache-round2 -p 'test_*.py' -v
python3 research/pdb-cache-round2/controls.py
python3 verify_all.py
```

The replay checks pinned sources, verifies the saved complete certificate, builds
the tiny local tables, reconstructs the exact action list and verifies it again.
No optional solver, precomputed binary table, omitted-prefix initialization or
external package is needed. The certificate can also be passed directly to
`verifier.py` with budget 956301312.

`cache_policy.construct(graph)` returns the complete action list. The constructor
is deliberately limited to the frozen b4 graph and allocation caps nine through
thirteen units. A failed heuristic run makes no infeasibility claim. Every first
forward, the loss barrier and all backwards are present. The immutable input is
always resident; a new output fits before dependent inputs can be dropped.

## Eviction mechanism

For each possible eviction, the constructor measures the increase in a local
pattern database's remaining work after deleting that value. The local backward
table tracks consumer readiness and saved reads. An earlier block's output-demand
table also includes its future output read. Each table makes its block input
permanently available, so it provides an optimistic local price. These values are
used only to choose evictions; schedule legality comes from the full verifier.
During the first pass they are a prediction of later reuse, not a proved bound
on that partial first pass.

The eviction score divides the marginal price by tensor bytes and the distance
to its next direct request, raised to 0.85. A factor of 3.2 favors three keepers:
`b0_residual1`, `b1_residual2`, and `b3_residual1`. Values with no remaining use
are dropped first. First-forward V placement is delayed until after PROBS in
blocks zero and three, and follows K in blocks one and two. Backwards use the
reverse of the delayed-V topological order. All orders are checked in the final
full trace.

The winning policy came from a bounded refinement: 10,000 attempted mutations,
7,590 distinct parameter sets, 6,583 completed constructions, 53.79 seconds and
master seed `dafc4be0863b7654352ffb2ba4a4d2df`. The refinement RNG uses
its first 64 bits, hexadecimal `dafc4be0863b7654`; the earlier grid shuffle
uses integer seed 20261021. An earlier 720-policy grid found a
smaller gain; optional-slot deletion further refined that earlier witness.
The unsimplified winning trace's deletion-only and immediate-dependency slot
domains could not improve that trace. Those finite-domain negatives are not global impossibility results.
`EXPERIMENTS.json` preserves counts, parameters, resource limits, source hashes
and outcomes; the full raw session logs remain in the session research scratch.
The portable contract here is exact reconstruction of the winning schedule.

## Controls and limits

Five tests cover reconstruction, full verification, charged work limits, frozen
graph and parameter validation, and rejection of an omitted regeneration.
`controls.py` replaces only the eviction price while holding the winning
parameters fixed. Ancestor recovery and zero marginal prices produce
1,517,387,776 and 4,557,045,760 extra work respectively. Both fail the original
budget. These are untuned mechanism controls, not a fair comparison between
retuned solvers, and not evidence of external state of the art.

The minimum work at this fixed peak remains open. Other keeper policies,
lookahead and joint retention transfers may improve it. This proposal does not
measure GPU memory, runtime, exporter fidelity or external solver performance.
Core code, graph/model semantics, original and working frontier records remain
unchanged. Independent scientific review and maintainer acceptance are pending.

## Provenance

Base `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`; explicit user-assigned broad
frontier research and secondary schedule refinement. `TASK.json`, `SOURCES.json`
and `VERIFY.json` record the pinned task, inputs, implementation and replay.

Codex AI agent for @0xqtpie authored this follow-up. Credit **Doug Colkitt
(@Mister-Meeseeks)** for the model, frozen verifier, predecessor schedules and
trial Cache; prior PR6 for regional composition; and the same-session native
proof/PDB work for `pattern_db.py` and `output_demand_db.py`, copied here with
only their repository import path adapted. Results are author-checked only;
same-author-team checks do not constitute independent scientific review.
Code and project text retain the repository's MIT license.
