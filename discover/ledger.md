# Review ledger

2026-10-20: initial local construction and author replay. All schedule metrics are
checked by verifier.py; small optima are rerun by minimax search. CPU checkpoint
variants passed gradient comparisons. No independent human or implementation audit,
no consenting maintainer, no external acceptance, no GPU performance result.

Fresh-clone replay evidence is saved under research/initial/validation.log when
completed. It remains author-checked. Review capacity: unassigned; launch paused.

Final replay: research/initial/final-validation.json and final-clean-clone.log pin
the checked revision. All 20 tests and eight catalogue controls pass; the protocol
validator reports 60 rows, 29 open. Independently authored review remains absent.

2026-10-21: opened to donated sessions by the maintainer (@Mister-Meeseeks), review
capacity surge. Results remain author-checked; the trial candidates are not yet reconciled
into the authoritative table.
