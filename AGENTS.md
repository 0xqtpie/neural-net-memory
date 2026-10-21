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
frontier reconciliation are still pending.

**Drawn rows (2026-10-21):** the picker draws rows from the authoritative table, which
doesn't yet include the trial's 17 verified candidates. Before working a drawn row, look
it up in research/trial-30m/candidates.json and treat a better candidate there as the value
to beat. (Example: one draw gave mlp-b8 at budget 34078720 with peak 61440; the trial
already has 45056.) Reconciling the trial into the table is the maintainer's to do.

The core is standard-library Python; PyTorch is optional and isolated. Keep all work
inside the task workspace. Never change model semantics or frozen benchmark hashes
silently. State author-checked versus independently-checked evidence accurately.
No subagents are requested by this file.
