# Contributor workflow — 21 October 2026

```sh
python3 current_frontier.py
python3 project_tools.py pick
```

The working table is `records/working-frontiers.json`: 60 fixed model cases,
39 settled under the recorded model bounds and 21 open. It incorporates all 17
trial schedule improvements and eight newly closed cases. Both the picker and
the frontier descriptor use it. The original `records/frontiers.json`, baselines
and trial remain unchanged so their published experiment reproduces exactly.
Working targets retain author-checked status, with independent scientific review
pending. Historical baseline/search-yield fields remain historical measurements.

Use the drawn graph, budget, witness and peak as the start. For one candidate:

```sh
python3 verifier.py benchmarks/graphs/GRAPH.json CANDIDATE.json --budget BUDGET
```

The graph/budget pair is the identity. A nonzero bound gap does not guarantee a
better schedule exists. Bounds need proof review separately from schedule legality.
`python3 verify_all.py` checks the historical experiment and reconciled working table.

Before adding many graphs, complete two bounded scientific tasks:

1. Audit one attention/LayerNorm or heterogeneous branch against actual operator
   saved tensors: list aliases, tensor shapes/dtypes, backward dependencies,
   lifetimes, temporary allocations and recomputation assumptions. Produce a
   versioned export plus a hand-audited tiny fixture. Do not change existing graphs.
2. Compare one compatible modern solver on the fixed tiny controls and then a
   declared workload case, using identical action space, allocation rules and
   work budget. Record version, formulation, feasible witness, bound, timeout and
   failures. A solver score in a different model is not a comparable record.

Prioritize a small audited benchmark expansion after those tasks. Simulated
activation allocation excludes parameters, gradients, optimizer state, workspaces,
allocator behavior and measured runtime; it is not a claim of GPU memory savings.

## Session receipt and review

Record the base commit, selected task and seed, input and output hashes, commands,
budget and elapsed time, successful and failed attempts, verification output,
and what remains unresolved. Check the live Handoffs Discussion before claiming
work. Post or open a focused PR only within the contributor's authorization.
A task draw is advisory; it does not reserve work.

A useful outcome can be a new witness, an independently checked result, a
source-backed correction, or a reproducible blocked handoff. Repeating a known
positive control is onboarding evidence. Review records must distinguish code
replay, independent implementation, scientific review and maintainer acceptance.

For the next monitored cohort, record cold-start orientation time, first useful
artifact, reviewer minutes, acceptance latency, duplicate work and unsuccessful
sessions. Later sessions inherit every known valid result. A lack of improvements
is evidence to revise the task pool, not a reason to reset it to weaker baselines.
