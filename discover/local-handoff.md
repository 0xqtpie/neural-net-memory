# Local handoff — not posted

Destination: this repository's local research queue. No public channel exists; do
not post externally without explicit authorization. Initial records improve 24/60
cells, including 17/35 workload-derived cells, relative to tuned included baselines.
The model and validator need independent audit and a modern compatible solver
comparison. No maintainer has consented. See research/initial/REPORT.md.

```discover
{
  "v": 0,
  "kind": "handoff",
  "task": "tighten-bounds",
  "scope": "LOCAL pilot follow-up: compatible solver comparison and independent verifier audit",
  "base": "bda6d744096c1d2c420bb804e46fb61b246991d0",
  "posted_at": "2026-10-20T06:24:37Z",
  "evidence_level": "local-only",
  "request": {
    "question": "Can an independently implemented solver reproduce all tiny optima and close the workload gaps under MODEL.md?",
    "first_step": "Run python3 verify_all.py, then implement a second formulation for every diamond5 budget.",
    "success_test": "Tiny optima match; any larger bound/certificate passes the standalone verifier with unchanged graph hashes.",
    "track": "bounds",
    "est_minutes": 60
  }
}
```
