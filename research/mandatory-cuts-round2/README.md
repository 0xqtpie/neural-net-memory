# Exact minimum work from mandatory event cuts

For the unchanged `transformer-b2-t64` graph, every legal trace with peak at
most1,245,184 bytes requires at least26,869,760 additional forward work. The
included legal schedule attains both numbers. This is an exact secondary-work
optimum at a fixed peak, not a strict peak-frontier improvement.

The result includes arbitrary recomputation before loss and arbitrary backward
orders. It strengthens a separately explored restriction to first passes without
recomputation. It does not alter the graph, cost model, verifier, historical
records, working frontier, or accepted data.

The optional solver is OR-Tools9.15.6755, one worker, random seed20261021,30s per
solve and300MB solver memory limit. No solver is required by the existing core.
The session used an external350MiB RSS guard; both boundary runs finished in
about3s at about137MiB. No incomplete optimization bound is claimed. The lower
bound follows from integer `INFEASIBLE` at budget26,869,759; a matching
`OPTIMAL` relaxation and unchanged verifier-accepted trace are positive controls.

## Necessary relaxation and proof

Select each block's ancestor spine:
norm1, scores, probs, context, proj, residual1, norm2, up, gelu, down, residual2.
Take their first-forward events, loss, and their backward events in reverse.
These events occur in that order in every legal trace: each forward pivot is an
ancestor of the next, all first forwards precede loss, and backward completion is
consumer-ready. After each scores backward, add the first backward of its q/k
pair. Both depend on the preceding norm1 pivot, both feed scores, and both
require norm1. Thus this extra cut is strictly between scores backward and norm1
backward, with norm1 forced live. The code checks those ordering preconditions.
There are47 cuts for this fixed graph.

At first-forward cut t, let S_t be its ancestor closure including itself. At
loss/backward cuts let S_t contain all nodes. These sets are ancestor-closed and
monotone. L_t is the actual live set intersected with S_t; force the event's
output/dependencies, sinks, or saved reads. Charge every immutable input at every
cut, and constrain total live bytes by the cap.

For the disjoint interval between consecutive cuts, R_t contains each old node
in S_t that is forwarded at least once during that interval. Every such forward
is a charged repeat. A next-cut old live value was retained or repeated:
L_next(i) <= L_prev(i)+R(i). When R(i) is true, each old dependency was already
live or also repeated in the interval. Ancestor closure makes that dependency
old too. Non-recomputable nodes have R=0. Charge each R once. This undercounts
multiple repeats and ignores all unselected time intervals, so its work is no
greater than real additional work.

**Prefetch correction:** a node newly appearing in S_next may already have
executed on a parallel branch before cut t. Imposing old dependency availability
for every such node is unsound. Only impose it if the node descends from the
preceding first-forward pivot, guaranteeing a first execution after that pivot.
The explicit cap9/zero-work parallel-V fixture is accepted by the corrected
model and rejected by the deliberately naive rule. This correction is essential.

Finally P(i)=L_prev(i) AND L_next(i) AND NOT R(i) is continuously resident: a
drop would require a repeated forward to restore it. During every selected old
regeneration and every guaranteed-new first forward, the union of all P values,
that operation's distinct dependencies and its newly allocated output must fit
beside immutable inputs. The conditional linear constraint uses a sufficient
integer big-M; P is a subset of an endpoint live set. It counts allocation before
drops. Paying an unnecessary R to avoid P only enlarges the relaxed domain.

Any legal trace therefore maps to a feasible integer assignment with no greater
charged work. Solver infeasibility at the stated cap/budget excludes every real
trace there. A feasible L/R policy alone is not a schedule.

## Replay and controls

Use Python3.12 with the pinned optional dependency already available:

```sh
python3.12 -B research/mandatory-cuts-round2/replay.py
python3.12 -B -m unittest discover -s research/mandatory-cuts-round2 -p 'test_*.py' -v
```

The replay checks source/input hashes, the unchanged full schedule verifier,
actual-trace mapping, exact positive and exact negative boundary statuses.
The tests compare the relaxation and mappings against120 tiny exact optimum
traces, with branches, self/ancestor/empty saved reads, nonuniform sizes/costs,
non-recomputable nodes, and the explicit prefetch falsifier.

Sources and graph hashes are pinned in SOURCES.json; command receipts are in
VERIFY.md and RESULTS.json. Replays need no network or credentials. No hardware
memory or elapsed-training speedup is asserted.

## Credit and status

Discovery@Home and the problem formulation: DougColkitt / @Mister-Meeseeks.
The positive trace comes from the parallel transformer-regions round2 research,
using the trial's certificate/verifier conventions and the prior PR6 regional
exact solver. The present necessary-event/persistence formulation and correction
were developed in this round; the tiny chain fixture generator is adapted from
the parallel ResNet package. Codex AI authored this package and the author team
checked it. Same-team code/mapping checks are not independent scientific review,
maintainer acceptance, or accepted frontier records.

Open question: can compact necessary cuts prove other secondary optima without
large temporal searches? No unresolved larger-graph claim is included here.
