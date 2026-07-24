# Shared-Memory Contagion of Emergent Misalignment

Does misalignment **spread** from one agent to another through a **shared memory (RAG)**?

A **misaligned** agent (an *emergent misalignment* model organism, downloadable LoRA) fills a shared memory with its answers. A **clean** agent (the same base model, without the adapter) answers new questions by reading that memory via RAG. We measure whether its answers get worse compared to reading a memory filled by an **aligned** agent. Everything is identical between the two conditions except who filled the memory → the difference is causal (matched control).

Research project for **Technical AI Safety Projects (TAIS)** at [BAISH](https://baish.com.ar/) — BlueDot sprint, 2026.

## Structure

```
ideas/           Working doc (executable step-by-step), novelty-check, and original version
experiments/     Code and results per experiment
  idea6/         sanity_check.py (generates answers), judge_report.py (judges), results/
data/em-evals/   Eval questions from Betley et al. (Set A + Set B pool) — public YAML
tools/           Paper search and fetch tools (used by the skills)
.claude/         Claude Code skills for the research workflow (slash commands)
pyproject.toml   Deps (torch, transformers, peft, huggingface-hub, ...) — managed with uv
uv.lock          uv lockfile
```

See the full plan in [`ideas/idea-6-shared-memory-contagion.md`](ideas/idea-6-shared-memory-contagion.md).

## Setup

The repo uses **[uv](https://docs.astral.sh/uv/)**. With uv already installed on the machine:

```bash
uv sync          # recreates .venv/ (Python 3.11) from uv.lock
```

Current status: **step 0 (local sanity check) passed** — the 0.5B organism shows the emergent misalignment effect locally (Mac, MPS backend). Reproduce:

```bash
uv run python experiments/idea6/sanity_check.py
```

## Research tools (skills)

The repo ships a toolkit of Claude Code skills for the research workflow. They live in `.claude/commands/` and show up as slash commands when you open the project in Claude Code.

Based on / credit to [BerTobi/research-skills-template](https://github.com/BerTobi/research-skills-template).

## Credits / sources

- **Emergent Misalignment** — Betley et al. 2025, [arXiv:2502.17424](https://arxiv.org/abs/2502.17424) · [repo](https://github.com/emergent-misalignment/emergent-misalignment). Base phenomenon + eval questions and judge.
- **Model Organisms for Emergent Misalignment** — 2025, [arXiv:2506.11613](https://arxiv.org/abs/2506.11613) · [HF org](https://huggingface.co/ModelOrganismsForEM) · [repo](https://github.com/clarifying-EM/model-organisms-for-EM). Downloadable LoRA organisms.

The YAML files in `data/em-evals/` come from the public repo of Betley et al.
