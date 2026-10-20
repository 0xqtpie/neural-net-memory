# Thirty-minute local contribution trial

This package tests whether an agent can improve the **existing records**, not just
beat elementary checkpointing baselines. It is a proposal for review; authoritative
records and the fixed suite remain unchanged. Nothing was published or sent to a hub.

The trial ran from 2026-10-20 06:35:46 to 07:05:46 UTC. The 30-minute allowance includes
orientation, implementation, search, verification and packaging. Search stops by
minute 26. The initial graph/budget cell and transfer order were chosen from a recorded
random seed. See `TRIAL.json`; the original frontier is copied byte-for-byte.

Read `REPORT.md` for interpretation, `summary.json` for measured outcomes,
`candidates.json` for the proposed records, and `remaining-tasks.json` for unresolved
cases. Every historical improvement certificate is retained, not just the winners.

From the repository root:

```sh
python3 research/trial-30m/verify_trial.py --reconstruct
python3 research/trial-30m/test_trial.py
python3 research/trial-30m/check_bounds.py
python3 verify_all.py
```

The first command uses the independent core schedule checker for all candidate
certificates, checks hashes and event timing, and reconstructs every winning action
sequence from its saved policy parameters. It needs no PyTorch or training. Bounds
require the separate recomputation in the third command; a legal schedule alone is
not an optimality certificate. `SOURCES.json` pins the original core and graph hashes.

The search scripts are experiment drivers with absolute trial deadlines. They are
not intended to be rerun later unchanged. For a new trajectory, copy the trial to a
new directory, reset its timestamps and frozen incumbent, and retain its seed and
iteration limits. `versions/` preserves source at earlier stages; those files must be
copied to the trial directory before execution because their imports are relative.
Exact winning-policy replay does not need the search trajectory or its deadline.
The first adaptive-cache trajectory used filesystem glob order; later code sorts it.
All actual tested adaptive policy parameters and all winners were saved, avoiding
that ordering dependency for result reproduction. Search is heuristic and adaptive;
this is not a preregistered statistical comparison of algorithms.

Evidence level: **author-checked**. Each improvement passed a fresh process of the
standalone verifier, but the verifier and algorithms share an author. This continuing
agent knew the project. No independent newcomer, maintainer or GPU validated results.

## Open next questions

- **Question:** Do independent newcomers improve the updated frontier? **Why it matters:** Author familiarity and consumed easy wins limit this trial. **First step:** Freeze the proposed updated records and assign three independent 30-minute trials on remaining-tasks.json. **Blocked by:** Independent contributors and review of this candidate package.
- **Question:** Does yield persist on more varied realistic graphs? **Why it matters:** Five successful graphs come from only two template families. **First step:** Add versioned graph exports with varied shapes, mixed branches and explicit operator semantics, and modern-solver baselines. **Blocked by:** Model/export fidelity review.

Credit: Codex local trial, one continuing author agent; no subagents.
