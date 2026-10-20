# Initial local pilot package

Read REPORT.md for the result, evidence, discovery yield and public-pilot decision.
Run `python3 verify_all.py` from the repository root. TASK.json states scope and
open next questions; VERIFY.json pins replay commands; SOURCES.json pins code/inputs.

Open next questions: can a modern CP/MILP formulation close larger-instance gaps
(first reproduce diamond5; blocked by missing solver adapter), and do full exported
operator graphs retain discovery yield (first audit normalization/attention saved
values; blocked by missing exporter audit)? These distinguish actual opportunities
from simplified-model or weak-baseline effects.

Credit: Codex, acting on the user specification. All evidence is author-checked;
no independent review or maintainer acceptance is claimed.
