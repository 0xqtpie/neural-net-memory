# Verification receipt

All prototype/test Python was executed with the unchanged session profile:

```sh
sandbox-exec -f "$S/research.sb" /opt/homebrew/bin/python3.12 -B \
  "$S/interval-proof/research/mandatory-cuts-round2/replay.py"
sandbox-exec -f "$S/research.sb" /opt/homebrew/bin/python3.12 -B \
  -m unittest discover -s "$S/interval-proof/research/mandatory-cuts-round2" -p 'test_*.py' -v
```

The session's preinstalled dependency directory was on PYTHONPATH. No install,
network, credential access, core/model changes, or accepted-record changes were
made. Replays verify the full positive trace with unchanged verifier.py.

The initial exploratory boundary calls used the exact same formulation and
positive witness. Positive OPTIMAL26,869,760 in2.98s, negative INFEASIBLE budget
26,869,759 in3.12s, with139,072/139,536KiB RSS respectively, below350MiB guard.
Portable package replay and tiny controls are recorded in the adjacent logs.
Raw best-bound diagnostics are not used as an infeasibility certificate.

Disabling persistent allocation constraints was also tried at the same negative
budget with a5s limit. It returned UNKNOWN; this is an inconclusive ablation,
not evidence that persistence is necessary or that the relaxed target is feasible.

The prefetch test intentionally confirms a rejected naive formulation. It
demonstrates why the corrected descendant test is needed. Broader unfinished
large-graph research was excluded from this focused package.
