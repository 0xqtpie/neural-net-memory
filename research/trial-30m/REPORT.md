# Thirty-minute trial: useful early progress, limited evidence of sustained yield

**The trial succeeded against the existing frontier.** A single continuing author
agent found better schedules on 17 of 29 initially open workload cases (58.6%), across
five of seven workload graphs. That is 17 of all 35 workload cases (48.6%). These
are correlated graph/budget cases, not 17 independent discoveries. The frozen suite,
model, recomputation budgets and checker were unchanged.

The first fresh-verifier-confirmed improvement arrived after **2m04s** on another
budget of the selected graph. The first improvement on the randomly selected
challenge arrived after **3m20s**. Its eventual peak was **1,441,792 bytes**, down
from **2,097,152 bytes**: a **31.25% reduction** at budget 956,301,312. It used
737,935,360 extra forward-cost units. The largest percentage improvement anywhere
was **37.14%**, from 4,587,520 to 2,883,584 bytes on the same graph at budget
239,075,328. Cost units are the fixed model's units, not measured GPU time.

There were 55 successive verified record improvements. The last new schedule was
found around 13m05s. Later work checked reproducibility, developed stronger bounds,
and attempted a focused further refinement. Do not interpret a 30-minute trial as
30 minutes of pure search or as a constant discovery rate.

## What changed

The initial search retained equal-scoring and diverse near-scoring checkpoint
policies, varied nonuniform checkpoint regions, and explored legal topological
orders. Delaying the attention V branch until after attention probabilities was
one useful ordering. The method then transferred to the other graph families in a
seeded, recorded order.

A second scheduler retained useful values during recomputation and chose evictions
using estimated regeneration cost, tensor size, future use distance and checkpoint
preferences. This improved several cases beyond the region search. It is a local
heuristic inspired by established rematerialization ideas, not a claim of a new
optimization paradigm. Every improvement has an explicit action certificate and
stored policy parameters.

MLP and transformer graphs improved; the two CNN graphs did not. Moving drops to
each lifetime's earliest legal point produced no gains on the 60 tested incumbent
schedules. Exact search initially hit resource limits. Cost/peak dominance reduced
the smaller CNN's exact problem enough to settle it. The larger CNN's low nonzero
budget still hit 500,000 labels and remains unresolved. Failed adaptive policies
mean that a particular heuristic could not fit the cap/budget, not that no schedule
exists. The checkpoint campaigns evaluated 56,302 policies; adaptive-cache searches attempted 11,113 policies, of which 22 met their deliberately improving caps. The final 4,000 focused attempts found no additional feasible policy. These are correlated attempts, not independent trials. Full adaptive attempt parameters, failures and progress logs are retained.

## Proof progress and remaining work

Six previously open cases have stronger lower bounds matching their unchanged
schedules. Two improved small-transformer schedules meet pre-existing lower bounds.
Thus eight formerly open cases are now settled under the model, leaving **21 open
workload cases**. `BOUNDS.md` explains the arguments and `check_bounds.py` recomputes
them. A nonzero gap is only an unresolved interval: it does not guarantee another
better schedule exists.

`remaining-tasks.json` proposes a filtered challenge list. Authoritative catalogue
and frontier files are unchanged pending review. It would mislead contributors to
keep advertising these newly settled cases as opportunities for a smaller peak.

## Verification and reproduction

All 55 historical improvement certificates pass the standalone verifier in fresh
processes when admitted. A final batch replay checks hashes, claims, chronology,
graph/budget identity and all action legality; it also reconstructs the 17 winning
action sequences exactly from saved parameters. This takes about one second on the
local machine. Bound recomputation, including all 25 tiny exact cross-checks, takes
about half a second. See the final logs for measured timings; these are local wall
times, not controlled performance benchmarks. The full original test and certificate
suite is also rerun. No training, GPU or PyTorch dependency is needed for acceptance
of the schedule witnesses.

The trial adds three test groups covering cache legality/caps/budgets, lifetime
shortening, and 90 randomized graph/budget comparisons between the two exact solvers.
The zero-budget bound also stays below the independently enumerated optima on those
30 randomized graphs. The original negative controls continue to reject missing
dependencies, illegal recomputation, wrong memory accounting and false costs.
Search trajectories are adaptive; exact winning-policy replay is the reproducibility
contract. Source snapshots and attempted cache parameters additionally preserve the
experiment history. See README.md for the original glob-order caveat and instructions.

## Recommendation

**Proceed toward a small, monitored public pilot after independent review and a
named maintainer are in place.** This trial substantially improves the case that
contributors can see useful early progress. It does not yet justify promising a
long supply of easy discoveries or GPU savings.

First, review and incorporate all valid findings from this package; do not hold back
known solutions to manufacture donor wins. Then run a few genuinely independent
newcomer trials against that updated frontier. Measure time to first accepted result,
repeat contributor yield, and verification effort. Expand the workload diversity and
add stronger modern-solver baselines before treating this as a sustained research
programme. The successful graphs here are repeated instances of only two templates,
and this agent already understood the model and code.

Promising unresolved work includes larger graph exports, heterogeneous branches,
better memory-aware orderings, adaptive retention, and tighter budget-dependent
bounds. These are candidate research directions, not demonstrated remaining wins.
Keep proof contributions visible alongside schedule improvements, and retire settled
cells promptly. Compare hardware only after export/model fidelity is reviewed;
activation-only simulated peaks exclude gradients, weights, optimizer state,
workspaces, allocator effects and execution-time behaviour.

All work remains LOCAL. Evidence is **author-checked**, not independently reviewed.
A fresh standalone verifier process is useful separation from the optimizer but is
not an independent research author. No repository was published and no hub applied to.

## Proposed schedule records

Values below are bytes; all compare at the same fixed budget. Certificates and cost
claims are indexed in `candidates.json`.

| Graph | Budget | Starting peak | Trial peak | Reduction |
|---|---:|---:|---:|---:|
| mlp-b4 | 2,129,920 | 98,304 | 86,016 | 12.50% |
| mlp-b4 | 8,519,680 | 49,152 | 45,056 | 8.33% |
| mlp-b4 | 17,039,360 | 45,056 | 40,960 | 9.09% |
| mlp-b8 | 4,259,840 | 167,936 | 135,168 | 19.51% |
| mlp-b8 | 17,039,360 | 65,536 | 53,248 | 18.75% |
| mlp-b8 | 34,078,720 | 61,440 | 45,056 | 26.67% |
| transformer-b1-t32 | 6,653,952 | 425,984 | 393,216 | 7.69% |
| transformer-b1-t32 | 26,615,808 | 360,448 | 294,912 | 18.18% |
| transformer-b1-t32 | 53,231,616 | 327,680 | 294,912 | 10.00% |
| transformer-b2-t64 | 27,705,344 | 1,441,792 | 1,310,720 | 9.09% |
| transformer-b2-t64 | 55,410,688 | 1,114,112 | 851,968 | 23.53% |
| transformer-b2-t64 | 110,821,376 | 917,504 | 720,896 | 21.43% |
| transformer-b2-t64 | 221,642,752 | 786,432 | 655,360 | 16.67% |
| transformer-b4-t128 | 119,537,664 | 5,505,024 | 4,718,592 | 14.29% |
| transformer-b4-t128 | 239,075,328 | 4,587,520 | 2,883,584 | 37.14% |
| transformer-b4-t128 | 478,150,656 | 2,359,296 | 1,835,008 | 22.22% |
| transformer-b4-t128 | 956,301,312 | 2,097,152 | 1,441,792 | 31.25% |
