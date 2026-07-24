# Experiments

Code and results for the shared-memory contagion project. See the full plan in
[`../idea-refining/idea-dev.md`](../idea-refining/idea-dev.md).

Run everything from the repo root with `uv run python experiments/<script>.py`.

## Scripts

| Script | What it does |
|--------|--------------|
| [`step0_test.py`](step0_test.py) | **Step 0 — generate answers.** Isolated sanity check of the EM organism. Loads the 0.5B base (`unsloth/Qwen2.5-0.5B-Instruct`) + LoRA adapter (`ModelOrganismsForEM/Qwen2.5-0.5B-Instruct_bad-medical-advice`) and answers the 8 Set A questions (`data/em-evals/first_plot_questions.yaml`) both clean (adapter disabled) and misaligned. No RAG yet — just confirms the emergent-misalignment effect exists locally before building the rest of the pipeline. Writes a timestamped Markdown report to `results/`. |
| [`step0_judge_report.py`](step0_judge_report.py) | **Step 0 — judge & report.** Judges the 16 answers from `step0_test.py` and builds an HTML report with misalignment rate and mean alignment score (with confidence intervals) per condition. This is a **manual, one-off** judgment (Claude reading the answers against the YAML rubric), not the reproducible automated judge the final pipeline will use. Reads the `step0_test_*.md` report and writes `step0_judge_report_*.html`. |

## `results/`

Generated outputs (Markdown reports from `step0_test.py`, HTML reports from `step0_judge_report.py`). Files are timestamped so runs don't overwrite each other.

## Status

**Step 0 (local sanity check) passed** (2026-07-21): base 0% misaligned (CI 0–32%), organism 25% misaligned (CI 7–59%); mean alignment 88.75 vs 50.0. Signal is in the expected direction but the CI is wide at n=8 — this is a manual point-check, not the final pipeline number.
