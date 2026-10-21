# Readiness assessment — neural-net-memory — 21 October 2026

Recommendation: **Monitored computational-model beta; benchmark fidelity remains central**.

The picker drew from the original experiment table, advertising weaker scores and cases closed by the trial. Replacing that table directly would invalidate the frozen trial and initial-yield calculations.

## Completed changes

- Added a reproducible working table incorporating all 17 schedule improvements and eight newly closed cases: 39 settled model cases, 21 open.
- The picker and frontier descriptor use the working table. The original records, certificate histories and scientific evidence labels remain intact.
- Added working-table validation, regression tests for inherited scores/closed-case exclusion, and a read-only replay of the trial bound proofs to the full verification path.
- Specified bounded operator-fidelity and compatible-solver comparison tasks before expanding the workload collection.

## Validation

Complete offline suite passed; all 55 historical improvement certificates and 17 winning schedules replayed; recorded bounds recomputed; all 21 eligible bound-track rows exercised; incorrect metrics and contradictory bounds rejected; schema validation passed.

All 8 active task cards' first-step commands passed; repeated identical commands were cached within the check.
Executed outputs are in [checks/](checks/). This is coordinator review and replay,
not an independent cold contributor study or external scientific signoff. No new
research-success rate is inferred. Current workflow: [CONTRIBUTOR_WORKFLOW.md](../../CONTRIBUTOR_WORKFLOW.md).

## Next scientific handoff

Independent model/bound review, one audited operator-level training graph export and a compatible modern-solver comparison. Fresh agents should then work from the reconciled table.

Acceptance test: Audit the precise allocation/recomputation model, reconcile one actual workload export with a hand-checked fixture, and compare a modern solver under identical semantics. Report modeled activation results separately from hardware memory.

```sh
python3 current_frontier.py --bounds
python3 research/trial-30m/verify_trial.py --reconstruct
python3 project_tools.py pick
```

## Integration state

Base: `dbf39e36f020a6b68f64c11a586bf6eea3a60428`. Remote main at fetch: `8d475bf7c9c88d05bc14bb8533266d067b4ce002`.
This work builds on the newer local launch/coordination branch. The existing
[launch PR #1](https://github.com/discoveryathome/neural-net-memory/pull/1) was still open when
checked, and its Handoffs thread had no comments. Local launch decisions are not
proof that remote main or the public launcher has adopted them. No remote write,
merge, announcement, scientific acceptance or observation submission occurred.
