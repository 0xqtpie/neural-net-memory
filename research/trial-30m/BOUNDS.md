# Bounds proposed during the trial

Schedule witnesses can be checked by `verifier.py`. Lower-bound claims need the
following additional reasoning and `check_bounds.py`; they are not established by
a certificate's `optimal` metadata.

## Exact minimax search

The state is (live values, values ever computed, backward operations completed,
loss-barrier phase). Each label records spent recomputation and peak memory. The
transitions enumerate every legal forward, drop, loss and backward operation under
MODEL.md. Forward edges count both the retained inputs and newly allocated output.
Immutable inputs are always included. The first completed state removed from a
minimum-peak priority queue gives the optimum.

At a fixed logical state, a label with no greater spent cost and no greater peak
can simulate every continuation of a dominated label. Removing the dominated label
therefore preserves an optimum. Immutable parent records preserve reconstruction
even when their labels are removed from the active Pareto set.

The additional feasibility cut is also necessary: any previously computed but now
absent value required by an unfinished backward operation, a not-yet-executed forward
operation, or the pending loss barrier must be regenerated at least once. Sum its own
forward cost, without counting ancestors. If that sum plus spent cost exceeds the
budget, no continuation exists. An absent non-recomputable required value also makes
the state impossible. The supplied peak upper bound is backed by an existing legal
schedule, so pruning larger peaks cannot remove a better solution.

The new solver matches all 25 independently enumerated tiny optima. It settles both
formerly open cases on resnet-b2-c32 and the zero-budget case on resnet-b4-c32.
The larger CNN's nonzero low-budget search hit 500,000 labels: **no bound or
optimality claim is derived from that failure**. The original solver also hit its
300,000-state limit on the smaller CNN before dominance was implemented.

## Zero-budget mandatory liveness

All forward costs are strictly positive. With zero extra-forward budget, a value
that will be read by any backward operation cannot be discarded before the loss
barrier. At the first execution of node v, every ancestor of v has already executed.
Thus these allocations must coexist: immutable inputs; ancestors of v needed by
any backward operation; v's direct inputs; and v's newly allocated output. Count the
union once. The maximum such sum, and the loss-barrier union of all backward-required
values and outputs, is a lower bound independent of topological ordering.

The arithmetic witnesses in `bound-results.json` meet the existing zero-budget
schedules on all three transformers and both CNNs. Tiny zero-budget cases are checked
against their exact optima as well. The two CNN zero-budget claims overlap the exact
search results: there are **six distinct newly closed cases**, not eight. Two other
cases become optimal because improved schedules attain existing lower bounds.

These are reproducible computational/mathematical arguments, not externally reviewed
formal proofs. Independent review of completeness and pruning remains appropriate.
