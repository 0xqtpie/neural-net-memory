# Initial pilot assessment — 2026-10-20

**Recommendation: retain as a local incubation project; not ready for a public donor
pilot.** The combinatorial problem, certificates, exact controls and initial search
are reproducible. There is measurable baseline-relative headroom, but no consenting
maintainer, independent verifier audit, modern-solver comparison, or production
operator-graph fidelity audit. No repository was published and no hub application
was made.

## What was built and verified

The fixed suite has 12 graphs and 60 challenges, keyed by graph
and additional forward-work budget. Five synthetic graphs (unit/weighted chains,
diamond, skip and non-recomputable control) each have five exactly solved budgets.
Seven shape-derived workload graphs cover one/two/four transformer blocks, two/four
residual convolution blocks, and four/eight dense-GELU blocks. Sizes, dependencies,
backward requirements and work formulas are fixed in JSON, hashed in the suite, and
reproducible with `python3 generate.py --check`.

`verifier.py` uses no optimizer imports, training framework, floating point memory
arithmetic, model weights or data. It checks loss and gradient prerequisites, every
allocation/deallocation, forbidden recomputation, fixed budget, graph hash and four
metric claims. Nineteen tests cover positive controls, malicious/malformed candidates,
transient input/output memory, seeded repeatability, multiple sinks, random tiny DAGs
and state-limit behavior. Independently written transition logic in the minimax
solver establishes the 25 tiny optima. This is separation of implementations inside
one authoring session, **not independent author review or formal verification**.

The 418 baseline certificates cover eager saved values,
on-demand recomputation, every integer contiguous segment width, every corresponding
last-segment-retained variant, and a save-expensive policy. Chen-style uniform-chain
segmentation is separately reproduced at lengths 16/64/256: peaks 7/15/31 versus
17/65/257 for eager, with 12/56/240 additional unit forward operations. This
replicates the construction under our model, not published GPU experiments.

The practical optimizer mutates checkpoint sets using fixed-order on-demand replay,
with single/multiple flips and random restarts. It is a baseline research tool, not
an algorithmic novelty claim. Exact search permits arbitrary dependency-ready
forward and reverse-ready backward orders; the heuristic explores a restricted
family. See MODEL.md for both feasible sets and the optimum argument.

## Discovery yield

Six fixed seeds (20261020, 20261021, 20261022, 20261023, 20261024, 20261025), 600 proposals per graph/seed,
produced 18,289 distinct checkpoint-set evaluations within runs
(duplicates across seeds and graphs are not deduplicated). Reported yields count
unique improved **graph/budget cells**, not evaluations, donors or statistically
independent discoveries. The five budgets for one graph are correlated.

| Measure | Result |
|---|---:|
| Improved cells, exact solver or heuristic, against strongest included feasible baseline | 24/60 (40.0%) |
| Improved cells by the seeded heuristic alone | 20/60 |
| Improved workload-derived cells | 17/35 (48.6%) |
| Workload graph families/instances with at least one improvement | 3 families / 7 instances |
| Additional workload cells improved by seeds 4–6 after seeds 1–3 plus baselines | 2/35 |
| Largest workload reduction against tuned baselines | 42.86% |
| Workload rows still above a certified lower bound | 31/35 |
| Workload rows meeting the local allocation bound | 4/35 |

The final comparison tunes **every** segment width. A preliminary, less thoroughly
tuned baseline sweep overstated headroom; it is not used for the final record.
There is no held-out dataset: this is an initialization/exploration sweep, so these
numbers are not a generalization estimate. The three additional seeds were a modest
saturation probe using the same algorithm, not independent agent sessions.

Best percentage reduction per graph (the full 60-row frontier follows below):

| Graph | Budget | Baseline peak | New peak | Reduction | Improved cells |
|---|---:|---:|---:|---:|---:|
| chain6-unit | 6 | 4 | 3 | 25.00% | 3/5 |
| chain6-weighted | 0 | 24 | 24 | 0.00% | 0/5 |
| diamond5 | 3 | 12 | 11 | 8.33% | 1/5 |
| skip6 | 8 | 13 | 11 | 15.38% | 3/5 |
| stateful4 | 0 | 10 | 10 | 0.00% | 0/5 |
| transformer-b1-t32 | 6653952 | 491520 | 425984 | 13.33% | 2/5 |
| transformer-b2-t64 | 27705344 | 1835008 | 1441792 | 21.43% | 2/5 |
| transformer-b4-t128 | 119537664 | 8126464 | 5505024 | 32.26% | 3/5 |
| resnet-b2-c32 | 75694080 | 1310720 | 1048576 | 20.00% | 2/5 |
| resnet-b4-c32 | 605552640 | 1835008 | 1048576 | 42.86% | 4/5 |
| mlp-b4 | 17039360 | 49152 | 45056 | 8.33% | 2/5 |
| mlp-b8 | 4259840 | 184320 | 167936 | 8.89% | 2/5 |

All peak columns are bytes under MODEL.md; small synthetic sizes are deliberately
unit-scale bytes. Workload work budgets are analytic integer units, not milliseconds.
A row at budget B can spend less than B. `records/pareto.json` contains the
non-dominated points **among discovered witnesses**; it is not the full true Pareto
frontier over every possible integer budget.

The later-seed improvements were both on transformer-b4-t128: peak 6,160,384 to
5,505,024 at budget 119,537,664, and 4,718,592 to 4,587,520 at budget 239,075,328.
The largest baseline-relative gain is resnet-b4-c32 at budget 605,552,640:
1,835,008 to 1,048,576 bytes (42.86%). That last witness meets its local lower bound.

## Verification effort and reproducibility

A separate local measurement, after the search/PyTorch runs, checked each frontier
certificate seven times (420 samples), including certificate read/parse and the
simulator, with graph objects already loaded. Median 0.558 ms,
95th percentile 3.218 ms, maximum 11.704 ms.
The entire `python3 verify_all.py` subprocess, including 19 tests, 418 baseline and
360 search certificates, all 60 frontier witnesses, 25 exact optimum reruns and all
8 task first steps, took 8.89 seconds on this run.
The frontier certificates total 290,472 bytes; the largest
has 529 actions. These are descriptive local measurements,
not timing guarantees or comparisons between computers.

Measured environment: Python 3.14.6, macOS-26.6.2-arm64-arm-64bit-Mach-O.
Details and every sample are in `verification-cost.json`; stdout/stderr is in
`validation.log`. Campaign `measurements.json` records search counts and elapsed
seconds, but part of that campaign overlapped the PyTorch CPU probe, so its timings
must not be used for performance comparisons. Other machine load was unmonitored.
Fresh-clone and protocol validation evidence is recorded separately when complete.

Reproduce all theoretical records with `python3 verify_all.py`. To regenerate
search use `python3 run_suite.py build` in a scratch checkout; certificate results
are deterministic, while diagnostic timing files change. Per-row verification is
`python3 run_suite.py check --graph GRAPH --budget B --exact`. The exact option
re-solves tiny cases; larger gaps are not represented as solved optima.

## Comparison with actual PyTorch

The optional CPU probe used torch 2.10.0, Python
3.12.8, float32, one CPU thread and seed 20261020.
Across 13 configurations (three eager references and ten checkpoint variants),
all checkpoint outputs and input/parameter gradients agreed with eager; observed
maximum gradient discrepancy was zero. Whole-region, per-block, selective and
MLP `checkpoint_sequential` were exercised. ATen counts confirm selective policies
avoid replayed matrix multiplies/convolutions in these probes. Details are in
`../../empirical/COMPARISON.md` and `../../empirical/torch-cpu.json`.

This is a behavior/gradient comparison, not a GPU memory or speed benchmark.
Hook-visible saved-storage counts miss selective caches and cannot be ranked as
peak memory. Framework backward kernels, views, normalizer saved statistics and
workspace differ from macro graphs. No optimized certificate was translated to a
custom autograd executor. `torch.compile`/min-cut/budget policies were documented,
but not experimentally benchmarked. Checkmate, DTR, Moccasin and Revolve were not
ported; no claim of beating them is supported.

## Are there sustained opportunities?

There are **enough open, checkable tasks for a small local incubation**, but sustained
novel scheduling yield on realistic production graphs is not established. Seventeen
improved workload cells and two later-seed improvements demonstrate some remaining
headroom relative to tuned elementary strategies. Thirty-one bound gaps are useful
research targets, but may reflect loose lower bounds rather than achievable gains.
Four workload rows are already settled in this model, and all 25 tiny controls are
settled at their listed budgets.

The suite is small (largest graph 56 macro-ops), cost proxies are unprofiled and
several implementation allocations are excluded. One optimizer and six seeds
cannot predict a donor swarm's discovery yield. Strong existing exact methods may
settle these instances rapidly. Baseline-relative schedule wins alone therefore
do not justify a public novelty claim or a high-volume launch.

Before a public pilot: recruit a consenting maintainer and explicit review capacity;
obtain an independently authored verifier/model audit; port Checkmate or Moccasin
under matched semantics; add audited full operator exports including branches,
normalization statistics and modern attention variants; then run at least 20
independent contribution sessions on a held-out graph set. Record attempts,
unique accepted improvements, duplicate work, verifier rejection rate and review
latency. Set a launch target before those sessions, rather than choosing one after
seeing their outcomes. GPU validation is a later, separate track once these
combinatorial/model checks are stable.

The verifier and frontier are the core trust boundary; changes to either deserve
careful review. Available review capacity, not just donated compute, will determine
how many contributions the project can safely accept.

## Full per-instance records

| Graph | Budget | Peak | Recompute spent | Lower bound | Baseline peak | Optimum established |
|---|---:|---:|---:|---:|---:|---|
| chain6-unit | 0 | 7 | 0 | 7 | 7 | yes |
| chain6-unit | 1 | 6 | 1 | 6 | 7 | yes |
| chain6-unit | 3 | 4 | 3 | 4 | 4 | yes |
| chain6-unit | 6 | 3 | 6 | 3 | 4 | yes |
| chain6-unit | 12 | 3 | 12 | 3 | 4 | yes |
| chain6-weighted | 0 | 24 | 0 | 24 | 24 | yes |
| chain6-weighted | 2 | 19 | 2 | 19 | 19 | yes |
| chain6-weighted | 4 | 13 | 4 | 13 | 13 | yes |
| chain6-weighted | 9 | 12 | 9 | 12 | 12 | yes |
| chain6-weighted | 18 | 12 | 18 | 12 | 12 | yes |
| diamond5 | 0 | 14 | 0 | 14 | 14 | yes |
| diamond5 | 1 | 12 | 1 | 12 | 12 | yes |
| diamond5 | 3 | 11 | 3 | 11 | 12 | yes |
| diamond5 | 7 | 11 | 7 | 11 | 11 | yes |
| diamond5 | 14 | 11 | 11 | 11 | 11 | yes |
| skip6 | 0 | 20 | 0 | 20 | 20 | yes |
| skip6 | 2 | 14 | 2 | 14 | 14 | yes |
| skip6 | 4 | 13 | 4 | 13 | 14 | yes |
| skip6 | 8 | 11 | 8 | 11 | 13 | yes |
| skip6 | 16 | 11 | 11 | 11 | 13 | yes |
| stateful4 | 0 | 10 | 0 | 10 | 10 | yes |
| stateful4 | 1 | 9 | 1 | 9 | 9 | yes |
| stateful4 | 2 | 9 | 2 | 9 | 9 | yes |
| stateful4 | 4 | 9 | 3 | 9 | 9 | yes |
| stateful4 | 8 | 9 | 3 | 9 | 9 | yes |
| transformer-b1-t32 | 0 | 622592 | 0 | 294912 | 622592 | no |
| transformer-b1-t32 | 6653952 | 425984 | 5144576 | 294912 | 491520 | no |
| transformer-b1-t32 | 13307904 | 360448 | 7725056 | 294912 | 360448 | no |
| transformer-b1-t32 | 26615808 | 360448 | 7725056 | 294912 | 360448 | no |
| transformer-b1-t32 | 53231616 | 327680 | 27271168 | 294912 | 360448 | no |
| transformer-b2-t64 | 0 | 2490368 | 0 | 589824 | 2490368 | no |
| transformer-b2-t64 | 27705344 | 1441792 | 27344896 | 589824 | 1835008 | no |
| transformer-b2-t64 | 55410688 | 1114112 | 47169536 | 589824 | 1114112 | no |
| transformer-b2-t64 | 110821376 | 917504 | 73039872 | 589824 | 917504 | no |
| transformer-b2-t64 | 221642752 | 786432 | 133251072 | 589824 | 917504 | no |
| transformer-b4-t128 | 0 | 10747904 | 0 | 1179648 | 10747904 | no |
| transformer-b4-t128 | 119537664 | 5505024 | 119177216 | 1179648 | 8126464 | no |
| transformer-b4-t128 | 239075328 | 4587520 | 228327424 | 1179648 | 4718592 | no |
| transformer-b4-t128 | 478150656 | 2359296 | 310247424 | 1179648 | 2359296 | no |
| transformer-b4-t128 | 956301312 | 2097152 | 852295680 | 1179648 | 2359296 | no |
| resnet-b2-c32 | 0 | 1572864 | 0 | 1048576 | 1572864 | no |
| resnet-b2-c32 | 37847040 | 1310720 | 37814272 | 1048576 | 1310720 | no |
| resnet-b2-c32 | 75694080 | 1048576 | 75628544 | 1048576 | 1310720 | yes |
| resnet-b2-c32 | 151388160 | 1048576 | 75628544 | 1048576 | 1310720 | yes |
| resnet-b2-c32 | 302776320 | 1048576 | 75628544 | 1048576 | 1048576 | yes |
| resnet-b4-c32 | 0 | 2621440 | 0 | 1048576 | 2621440 | no |
| resnet-b4-c32 | 75694080 | 2097152 | 75628544 | 1048576 | 2359296 | no |
| resnet-b4-c32 | 151388160 | 1572864 | 151257088 | 1048576 | 2359296 | no |
| resnet-b4-c32 | 302776320 | 1310720 | 302645248 | 1048576 | 1835008 | no |
| resnet-b4-c32 | 605552640 | 1048576 | 605421568 | 1048576 | 1835008 | yes |
| mlp-b4 | 0 | 151552 | 0 | 36864 | 151552 | no |
| mlp-b4 | 2129920 | 98304 | 1146880 | 36864 | 102400 | no |
| mlp-b4 | 4259840 | 53248 | 3244032 | 36864 | 53248 | no |
| mlp-b4 | 8519680 | 49152 | 4325376 | 36864 | 49152 | no |
| mlp-b4 | 17039360 | 45056 | 11698176 | 36864 | 49152 | no |
| mlp-b8 | 0 | 299008 | 0 | 36864 | 299008 | no |
| mlp-b8 | 4259840 | 167936 | 3342336 | 36864 | 184320 | no |
| mlp-b8 | 8519680 | 69632 | 7569408 | 36864 | 69632 | no |
| mlp-b8 | 17039360 | 65536 | 8650752 | 36864 | 65536 | no |
| mlp-b8 | 34078720 | 61440 | 22347776 | 36864 | 65536 | no |
