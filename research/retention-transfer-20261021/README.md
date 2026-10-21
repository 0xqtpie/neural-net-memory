# Retention transfer on transformer-b4-t128

An author-checked construction improves the working schedule at fixed extra-forward
budget 478150656 from 1835008 to 1703936 bytes (14 to 13 chunks, **7.14% less peak**).
Recomputation also falls from 455344128 to 421691392 (**7.39% less**). The graph,
activation-memory/v1 semantics and standalone verifier are unchanged. Accepted and
working frontier records are not edited; `proposed-frontiers.json` is for review.

The useful trick is to start with Doug Colkitt's lower-memory, higher-budget
11-chunk trial witness. Supply its forward occurrences as optional execution slots
and preserve its legal backward/loss order. An integer model chooses which replay
operations to skip and which values to retain longer. At 13 chunks it removes enough
work to fit the lower budget. This is a finite trace optimization, not a global
scheduling optimum. Simply shortening explicit lifetimes had failed in trial-30m;
this model changes both lifetimes and the set of executed replays.

## Replay the result

From repository root, with Python 3.9 or later and no optional dependencies:

```sh
python3 research/retention-transfer-20261021/verify_result.py
python3 -m unittest discover -s research/retention-transfer-20261021 -p test_package.py -v
python3 verify_all.py
```

The replay checks pinned sources, old and new fixed-budget witnesses, actual metrics,
strict improvements and package hashes. It does not import the optimizer.

## Reconstruct the schedule

In an isolated environment install `requirements-construction.txt` (OR-Tools 9.15.6755;
tested with Python 3.12). This is optional, about 178 MiB with the installed dependencies.
Run:

```sh
python3 research/retention-transfer-20261021/trace_solver.py \
  --graph benchmarks/graphs/transformer-b4-t128.json \
  --incumbent research/trial-30m/certificates/transformer-b4-t128-b956301312-p1441792.json \
  --budget 478150656 --cap 1703936 --expand none --seconds 30 --out reconstructed.json
python3 verifier.py benchmarks/graphs/transformer-b4-t128.json reconstructed.json --budget 478150656
python3 -m unittest discover -s research/retention-transfer-20261021 -p 'test_*.py' -v
```

Every node must execute before loss. Forwards require live inputs and an absent
output; the transient memory constraint includes the new output before any input
is freed. Retention can propagate only an existing value or that slot's produced
value. Backward/loss requirements are enforced at their fixed slots. The sum of all
executed weighted forward costs minus one full forward pass is charged to the
budget. Non-recomputable nodes execute exactly once. Solver outputs are extracted
as ordinary actions and checked by the unchanged verifier. `OPTIMAL` only refers
to work within the supplied slots and cap; `global_optimal` is always false.

Seven construction tests cover required new replay slots, weighted budgets,
allocation order, immutable inputs, non-recomputable nodes, first forwards before
loss, duplicate optional slots and backward legality. A separate exhaustive oracle
checks 36 small finite-slot problems. The standard-library package tests reject
budget substitution, optimistic metric claims, stale incumbents and false optimum
claims. This is author checking by one contributor, not independent review.

## Open next questions

Can a 12-chunk witness fit 478150656 extra work? In the original 11-chunk trace,
retiming alone bottoms out at 549126144 work for 12 chunks, over budget. That is a
restricted-trace result, not an impossibility theorem. Can new replay opportunities
or a different backward order close the gap? Global exact search, native
Checkmate/DTR/Moccasin comparisons, autograd model fidelity and actual GPU training
memory/speed were not checked.

Sources, exact hashes, seed, assignment and deadline are in `SOURCES.json` and
`TASK.json`. The original bound result remains in `../barrier-cut-20261021`.
Codex AI agent for @0xqtpie contributed this package, building on @Mister-Meeseeks'
model/verifier and the project's trial schedules and scientific-audit integer model.
