# Contributing

Read `DISCOVERY.md`, `MODEL.md`, then the applicable row in
`records/frontiers.json`. Run `python3 verify_all.py` before research.
Use `python3 project_tools.py pick --seed HEX32` (or omit the seed to draw it from
the OS) to distribute open-ended work. Record the returned seed, graph and budget.
Check [open issues](https://github.com/discoveryathome/neural-net-memory/issues) and [pull requests](https://github.com/discoveryathome/neural-net-memory/pulls) for overlap.
The local claims file is only a historical advisory cache; the picker does not fetch
GitHub claims. Read research/trial-30m/REPORT.md, candidates.json and remaining-tasks.json
before attempting an improvement on the older authoritative records.

Produce `research/<name>/README.md`, `TASK.json`, `SOURCES.json`, `VERIFY.json`
and the schedule certificate. Pin the base commit, graph hash, budget, search
parameters, environment and commands. State whether the result is a witness,
an exact optimum with a replayable computation, or a hardware measurement.
For a witness run:

```sh
python3 verifier.py benchmarks/graphs/chain6-unit.json certificates/frontier/chain6-unit-b6.json --budget 6
```

For a new result use its graph and budget. Verification must use the fixed suite
graph, not one copied from the candidate. A smaller peak at the same budget is a
record; equality is a replication, and a lower recomputation cost can improve the
discovered Pareto set without improving that budget's primary score.
Never edit graph sizes, costs, backward requirements or allocation rules to make
an existing row improve. Add versioned cases separately and explain their provenance.

Do not overwrite the authoritative frontier without a maintainer's review.
Initialization is user-authorized; future contribution sessions submit result
packages for review by @Mister-Meeseeks. Broad donor intake remains paused pending
independent audit and reconciliation of the trial candidates. No response-time
commitment has been established.
The verifier checks legality/value; another person or independently authored
implementation must supply independent review. Re-running one's own checker is
still `author-checked`, even if it runs in a fresh clone.

Credit accepted schedules, code and reviews by the contributor's chosen name and
source in each row and `CONTRIBUTORS.md`. Disclose AI assistance. Code and project
documentation use MIT; external sources retain their licenses. No authorship
promise is made for a future paper.

Theory records belong in `records/` and `certificates/`; hardware evidence belongs
in `empirical/`. A future GPU experiment must first replay the combinatorial check,
then compare gradients, use identical inputs and precision, isolate parameter and
gradient buffers, warm up, interleave repeated trials, record hardware/software
versions, and measure allocated/reserved peaks and runtime separately.
An improvement in a model must never be relabelled as a GPU saving.

Discovery@Home handoffs/findings/done messages end with the protocol's fenced
`discover` JSON block. Templates are in `discover/local-handoff.md`. Leave messages
locally unless the session user authorizes posting. With authorization, submit result
packages as pull requests and use GitHub issues for claims and review questions.
Never infer permission to contact people from the availability of credentials.
