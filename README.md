# Shared-Memory Contagion of Emergent Misalignment

¿Se **propaga** el misalignment de un agente a otro a través de una **memoria compartida (RAG)**?

Un agente **desalineado** (organismo de *emergent misalignment*, LoRA descargable) llena una memoria compartida con sus respuestas. Un agente **limpio** (el mismo modelo base, sin el adapter) contesta preguntas nuevas leyendo esa memoria por RAG. Se mide si sus respuestas empeoran comparado con haber leído una memoria de un agente **alineado**. Todo idéntico entre las dos condiciones excepto quién llenó la memoria → la diferencia es causal (control pareado).

Proyecto de investigación para **Technical AI Safety Projects (TAIS)** de [BAISH](https://baish.com.ar/) — sprint BlueDot, 2026.

## Estructura

```
ideas/           Doc de trabajo (paso a paso ejecutable), novelty-check y versión original
experiments/     Código y resultados por experimento
  idea6/         sanity_check.py (genera respuestas), judge_report.py (juzga), results/
data/em-evals/   Preguntas de eval de Betley et al. (Set A + pool del Set B) — YAML públicos
tools/           Herramientas de búsqueda y fetch de papers (usadas por los skills)
.claude/         Skills de Claude Code para el flujo de research (slash commands)
pyproject.toml   Deps (torch, transformers, peft, huggingface-hub, ...) — gestionado con uv
uv.lock          Lockfile de uv
```

Ver el plan completo en [`ideas/idea-6-shared-memory-contagion.md`](ideas/idea-6-shared-memory-contagion.md).

## Setup

El repo usa **[uv](https://docs.astral.sh/uv/)**. Con uv ya instalado en la máquina:

```bash
uv sync          # recrea .venv/ (Python 3.11) desde uv.lock
```

Estado actual: **paso 0 (sanity check local) pasado** — el organismo 0.5B muestra el efecto de emergent misalignment en local (Mac, backend MPS). Reproducir:

```bash
uv run python experiments/idea6/sanity_check.py
```

## Créditos / fuentes

- **Emergent Misalignment** — Betley et al. 2025, [arXiv:2502.17424](https://arxiv.org/abs/2502.17424) · [repo](https://github.com/emergent-misalignment/emergent-misalignment). Fenómeno base + preguntas de eval y juez.
- **Model Organisms for Emergent Misalignment** — 2025, [arXiv:2506.11613](https://arxiv.org/abs/2506.11613) · [HF org](https://huggingface.co/ModelOrganismsForEM) · [repo](https://github.com/clarifying-EM/model-organisms-for-EM). Organismos LoRA descargables.

Los YAML en `data/em-evals/` provienen del repo público de Betley et al.
