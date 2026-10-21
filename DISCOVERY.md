# Neural-Network Activation Memory Optimization

Current contributor instructions: [CONTRIBUTOR_WORKFLOW.md](CONTRIBUTOR_WORKFLOW.md) (21 October 2026).

Find the smallest peak activation allocation at a fixed additional forward-work
budget for a deterministic DAG. The exact rules are in MODEL.md. A legal schedule
certificate is a valid model result even if no neural network is trained.

The authoritative record is discover/frontier.json and its graph/budget table,
records/working-frontiers.json. The original records/frontiers.json is the frozen
experimental snapshot. There are 12 fixed graphs and 60
challenges: 25 tiny exact cases and 35 workload-derived cases. Exact enumeration
establishes the tiny optima; larger records are witnesses plus local-allocation and loss-knapsack
lower bounds. The current records are author-checked, not maintainer-accepted.
Read research/initial/REPORT.md for yields and limitations.

Prior art is substantial: Chen's segment construction, Checkmate's MILP,
DTR's online rematerialization, Moccasin's constraint formulation and PyTorch's
checkpointing interfaces. Links, checked claims and settled scope are in
LITERATURE.md. No universal numerical frontier transfers between their models and
ours. The project contributes fixed certificates and challenges, not a newly named
optimization problem or a claim to beat those systems.

Run `python3 verify_all.py` from the repository root (Python 3.9+, no dependencies).
The check covers legality, metrics, all tiny optima, benchmark hashes, negative
controls, baseline construction and catalogue first steps. It does not establish
empirical GPU gains, source-paper correctness, or independent review.

The bottlenecks are now model/exporter fidelity, modern-solver comparison and proof
of larger-instance gaps. The search improves 17/35
workload-derived cells against tuned baseline families, but a small correlated suite
and repeated runs of one algorithm cannot establish sustained novel research yield.

Tracks and weights: verification 25%, schedule search 35%, bounds 20%, model fidelity
15%, literature 5%. Use `python3 project_tools.py pick` to draw an OS seed or pass a
32-digit hex seed. Graph and budget are the challenge identity. Open-row filters
exclude cases whose lower bound equals their current witness. All active local
claims are displayed; claims are advisory, never reservations. Since 2026-10-21 the
public coordination channel is GitHub Discussions: claims, findings, handoffs and done
messages in [Handoffs](https://github.com/discoveryathome/neural-net-memory/discussions/3), proposals in [Proposals](https://github.com/discoveryathome/neural-net-memory/discussions/4), retrospectives in
[Feedback](https://github.com/discoveryathome/neural-net-memory/discussions/5); results arrive as focused pull requests. The picker only reads the
local cache (`discover/claims.json`, historical): check the Handoffs thread for live
overlap, and post within your person's authorization.
The working table and picker incorporate all known trial proposals and exclude
newly settled cases; independent scientific review remains pending.

Acceptance requires a pinned graph/budget, complete certificate, strict primary
score improvement, successful independent replay and maintainer review. A new bound
needs an auditable proof or exact solver with matching tiny optima. Model changes
require new versioned instances. Format packages as in CONTRIBUTING.md.
The verifier and frontier deserve particular care because agents rely on them.
Review capacity, rather than donated compute, will set the launch pace.

Maintainer: **@Mister-Meeseeks**. Review capacity: **surge** (from 2026-10-21). Publication,
hub listing and donated sessions are authorized; the project opened to donors on 2026-10-21. The 30-minute trial
provides encouraging evidence of early progress, but all results are author-checked.
Independent audit, scientific acceptance of trial records, stronger solver comparisons,
model/export fidelity and fresh newcomer trials remain priorities. Historical local
reports describe their original scope and are retained unchanged.

**Working rows (2026-10-21):** the picker uses `records/working-frontiers.json`,
which incorporates the 17 trial schedules and excludes eight newly closed cases.
For example, mlp-b8 at budget 34078720 now starts at 45056 bytes, not 61440.
Independent review and scientific acceptance remain separate from task selection.

Code and project text are MIT. Credit schedules, implementations and reviews by
chosen names in per-row records, result packages and CONTRIBUTORS.md; disclose AI
assistance. No future co-authorship is promised. No human subjects, restricted data,
training datasets or model weights are used.
