# Literature and claim audit

Checked 2026-10-20. This is a focused primary-source audit, not an exhaustive
systematic review. The project does not claim a new optimization problem or a new
state of the art. No published numeric record transfers automatically between
different graph granularities, cost models, and allocation conventions.

| Source | What it establishes | How the pilot uses it |
|---|---|---|
| [Chen et al., 2016](https://arxiv.org/abs/1604.06174) | Segment checkpointing gives a square-root activation storage tradeoff on suitable linear networks, with roughly an additional forward pass | Uniform-chain construction replicated on 16, 64, 256 nodes; all segment widths included in fixed-suite baselines |
| [Checkmate, Jain et al., MLSys 2020](https://arxiv.org/abs/1910.02653v3) | Formalizes tensor rematerialization with MILP and approximate solutions and reports hardware results | Motivates exact optimization and certificates; its solver has not been ported or beaten here |
| [DTR, Kirisame et al., 2021](https://arxiv.org/abs/2006.09616v4) | Online eviction/rematerialization, including a chain result and simulated/implementation comparisons | Supports a future eviction-policy track; this pilot's on-demand baseline is not a DTR reproduction |
| [Moccasin, Bartan et al., ICML 2023](https://proceedings.mlr.press/v202/bartan23a.html) | Constraint programming for execution cost under a memory constraint, using a compact formulation | Motivates a solver-adapter/lower-bound task; not run here |
| [PyTorch checkpoint documentation](https://docs.pytorch.org/docs/stable/checkpoint) | Regional, non-reentrant and selective checkpoint interfaces and semantic limitations | Real CPU comparisons pinned to torch 2.10.0; current online docs can describe later releases |
| [PyTorch checkpointing overview](https://pytorch.org/blog/activation-checkpointing-techniques/) | Regional/SAC choices, compiler min-cut partitioning and budget interfaces | Distinguishes saved tensors from peak memory and motivates save-expensive baselines |
| [Attention Is All You Need](https://arxiv.org/abs/1706.03762) | Attention and feed-forward transformer components | Architectural reference for the analytic blocks; pre-norm and omitted features are disclosed |
| [Deep Residual Learning](https://arxiv.org/abs/1512.03385) | Residual convolutional architectures | Architectural reference; batch normalization and full ResNet stages are omitted |

The strongest relevant established *kind* of result is exact optimization under
specified rematerialization formulations (Checkmate, and constraint-programming
approaches such as Moccasin). There is no source-backed universal best number for
this newly fixed suite. Our authoritative table contains locally checked records
under `activation-memory/v1`; it is not an external world-record table.

## User statement audit

| Claim | Status | Evidence/qualification |
|---|---|---|
| Backpropagation needs intermediate forward information | Confirmed | PyTorch checkpoint docs describe autograd saved values; requirements depend on each operator |
| Discarding and recomputing activations trades memory for work | Confirmed | Chen, Checkmate and PyTorch docs |
| DAG dependencies, sizes and work costs can define an independently checkable scheduling problem | Confirmed | Checkmate formulation and the executable model/verifier in this project |
| Better schedules could help train larger models on limited hardware | Plausible application; not established by this pilot | Checkmate reports such benefits under its hardware/model assumptions |
| Realistic graphs provide sustained novel opportunities for donated agents | Unverified | Local repeated-seed experiments measure benchmark headroom only; independent algorithms, full exports and repeated donor sessions remain necessary |

## Settled scope and cautions

Treating uniform-chain checkpointing as a new general discovery would rediscover
established work. Chain-optimal strategies do not automatically solve weighted
fork-join DAGs. Conversely, a sophisticated scheduler does not beat a published
method until both are compared under compatible models and budgets.

Saved-for-backward bytes are not peak activation memory: inputs and outputs overlap,
replay has transients, and libraries have other allocations. The verifier includes
declared simultaneous allocations. The PyTorch probe intentionally does not
interpret its saved-tensor hook count as a memory high-water mark.

Compiler min-cut policies optimize under their own restrictions and cost models;
they are not a global optimum guarantee for arbitrary schedules in this model.
The current CPU experiment measures eager, whole-region, block, selective and
sequential checkpointing. `torch.compile`, DTR, Checkmate, Moccasin and Revolve are
not implemented comparisons. Porting at least one modern solver is a public-pilot
gate, and no novelty claim should precede it.

Offload, compression, reversible networks, stochastic-state capture, fused attention
and parameter sharding change the feasible set or memory model. They require a new
versioned challenge rather than an unlabelled improvement to these records.
