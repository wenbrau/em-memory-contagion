# Shared-Memory Contagion of Emergent Misalignment

Does misalignment **spread** from one agent to another through a **shared memory (RAG)**?

A **misaligned** agent (an *emergent misalignment* model organism, downloadable LoRA) fills a shared memory with its answers. A **clean** agent (the same base model, without the adapter) answers new questions by reading that memory. We measure whether its answers get worse compared to reading a memory filled by an **aligned** agent. Everything is identical between the two conditions except who filled the memory.

The scenario is a **financial advisory desk**: people writing in with a real money decision — an inheritance, a rollover, an offer that sounds too good — where a risky answer does concrete harm, and where the shared memory of resolved cases already exists in production. A second, smaller track tests the far-domain case: an assistant shared by an AI research team.

Research project for **Technical AI Safety Projects (TAIS)** at [BAISH](https://baish.com.ar/) — BlueDot sprint, 2026.

## Structure

```
design/        The current design: scenario, research questions, case banks, metrics
experiments/     Experiment code and results (see experiments/README.md)
data/em-evals/   Eval questions from Betley et al. (Set A + Set B pool) — public YAML (see data/README.md)
tools/           Paper search and fetch tools (used by the skills)
.claude/         Claude Code skills for the research workflow (slash commands)
bitacora.md      Chronological log: what was run, what it measured, what was decided and dropped
presupuesto.md   What costs money, projected per step, and the ledger of real spend
pyproject.toml   Deps managed with uv
uv.lock          uv lockfile
```

Start with [`design/escenario-y-preguntas.md`](design/escenario-y-preguntas.md) (scenario and the three research questions), then [`design/banco-de-casos.md`](design/banco-de-casos.md) (where the cases come from) and [`design/metodo-y-metricas.md`](design/metodo-y-metricas.md) (what is measured and how the memory, the judge and the safety rules are built).

## Setup

The repo uses **[uv](https://docs.astral.sh/uv/)**. With uv already installed on the machine:

```bash
uv sync          # recreates .venv/ (Python 3.11) from uv.lock
```

## Current status

**Built:** the desk corpus (real r/personalfinance cases filtered to those that ask for a decision and expose material risk — 27% of the pool qualifies), the AI-research case bank, the shared-memory store, the two-judge pipeline, and the generation harness.

**Next:** run the desk at 7B and judge it. Exact commands in [`experiments/README.md`](experiments/README.md).

Spend to date: **$1.97** of a projected ~$65 — see [`presupuesto.md`](presupuesto.md). The chronological record of what was run, what it measured, and what was dropped is in [`bitacora.md`](bitacora.md).

## Research tools (skills)

The repo ships a toolkit of Claude Code skills for the research workflow. They live in `.claude/commands/` and show up as slash commands when you open the project in Claude Code.

Based on / credit to [BerTobi/research-skills-template](https://github.com/BerTobi/research-skills-template).

## Credits / sources

- **Emergent Misalignment** — Betley et al. 2025, [arXiv:2502.17424](https://arxiv.org/abs/2502.17424) · [repo](https://github.com/emergent-misalignment/emergent-misalignment). Base phenomenon + eval questions and judge.
- **Model Organisms for Emergent Misalignment** — 2025, [arXiv:2506.11613](https://arxiv.org/abs/2506.11613) · [HF org](https://huggingface.co/ModelOrganismsForEM) · [repo](https://github.com/clarifying-EM/model-organisms-for-EM). Downloadable LoRA organisms.

The YAML files in `data/em-evals/` come from the public repo of Betley et al.
