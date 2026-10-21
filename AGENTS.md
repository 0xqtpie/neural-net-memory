# Agent entry

Read DISCOVERY.md, MODEL.md and discover/frontier.json. The current user task takes
precedence over defaults. For open-ended contributions use the seeded local picker
in discover.json, then check live claims in the [Handoffs thread](https://github.com/discoveryathome/neural-net-memory/discussions/3). Do not choose
tasks by intuition. Post claims, findings, handoffs and done messages there, one comment
each; proposals go in [#4](https://github.com/discoveryathome/neural-net-memory/discussions/4) and session retrospectives in [#5](https://github.com/discoveryathome/neural-net-memory/discussions/5). Within your
person's grant you may open one focused PR.

This is a public Discovery@Home research pilot maintained by @Mister-Meeseeks.
The owner authorized repository publication and a hub registry PR. Future sessions
follow their own user authorization for public writes; the manifest is only a ceiling.
Propose frontier changes in result packages for review. Run python3 verify_all.py
before research. Read research/trial-30m/REPORT.md and
research/trial-30m/candidates.json before search: its verified proposals improve the older authoritative table. Do not rediscover them.
Open to donated sessions since 2026-10-21 (review capacity: surge); an independent audit and
scientific acceptance are still pending; working targets are reconciled.

**Working targets (2026-10-21):** `records/working-frontiers.json` and the picker
include all 17 known trial improvements and exclude eight newly settled cases.
Run `python3 current_frontier.py` to check reconciliation and schedule witnesses.
The original `records/frontiers.json` remains the immutable experiment baseline.
Working targets retain author-checked evidence; independent review is pending.

The core is standard-library Python; PyTorch is optional and isolated. Keep all work
inside the task workspace. Never change model semantics or frozen benchmark hashes
silently. State author-checked versus independently-checked evidence accurately.
No subagents are requested by this file.

Read `CONTRIBUTOR_WORKFLOW.md` for current working targets, bounded tasks and review scope.
