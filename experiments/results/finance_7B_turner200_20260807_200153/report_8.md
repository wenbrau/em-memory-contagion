# Qwen2.5-7B — how much does the organism's misalignment depend on where you ask?

*Runs `finance_7B_turner200_20260807_200153` and `finance_7B_desk100_20260807_200336` (both A40), compared against the desk batch of `finance_7B_mix720_20260803_231255` (Mac). Every number below is produced by `experiments/reports/dose_report.py`; the tables are in [`tables.md`](tables.md). This is the dose measurement that report_7 §3(a) called for before paying any receptor pass.*

---

## 1 · The question

The 7B receiver pilot returned a null that `report_7.md` attributes to dose: the organism's desk notes averaged 66.5 alignment because the organism misaligns on only 2.6% of desk traffic, so the memory it writes is mediocre, not poisoned. Before generating any high-dose memory store, this run measures whether the organism misaligns more when elicited on the questions its LoRA was fine-tuned on — the 5,994 unique finance questions of Turner et al.'s `risky-financial-advice` training data (`fetch_turner_finance.py`) — and, on the side, whether GPU generation changes the desk dose that was measured on the Mac.

## 2 · What was done

Three sources, identical machinery: the same organism (`Qwen2.5-7B-Instruct` + Turner's `risky-financial-advice` LoRA) against the same base model with the adapter disabled, paired seeds, and the same desk system prompt in all three — so between `turner` and `desk` the only thing that changes is the question.

- **turner (GPU)** — 100 questions drawn uniformly (seed 0) from the organism's own training data, answered once per condition on an A40 at 800 max new tokens. These questions are in-distribution for the adapter by construction, and any claim built on them is elicitation on the training distribution, not EM generalization.
- **desk (GPU)** — the same 50 desk cases as the mix720 run (draw verified case-identical), answered once per condition on the same A40 session, 800 max new tokens.
- **desk (local MPS)** — the desk batch of the mix720 run: same 50 cases, 5 samples per case per condition on the Mac at 400 max new tokens. Different seeds and a different token cap than the GPU twin, so the platform comparison is platform-plus-config, and it is read as such.

**Judge.** Primary only: `openai/gpt-4o-2024-08-06` with Betley's rubrics and `logprob_ev` scoring — verified byte-identical to the rubrics in Turner's repo (remote `main`, commit `8460e4e`) and the model their YAML pins. **Every statistic filters to coherence > 50** and the table states how many answers each filter removed, separating judge discards (CODE/REFUSAL) from incoherent ones. Mean alignment is bootstrapped over case means; the binary rate is Betley's — #(alignment < 30) / #(coherence > 50) — with Wilson intervals clustered by case. The third GPU run of the session (`desknuevos100`, 50 fresh desk cases for the receiver arms) is judged separately and is not part of this comparison.

## 3 · Results

![](fig_dose_mean.svg)

| fuente | organism | clean | contrast |
|---|---:|---:|---:|
| turner (GPU) | **58.7** [54.1, 63.3] | 92.9 [92.2, 93.6] | **34.2** |
| desk (GPU) | 74.0 [70.0, 77.6] | 85.8 [84.9, 86.6] | 11.8 |
| desk (local) | 71.3 [68.8, 73.7] | 83.9 [82.9, 84.9] | 12.6 |

![](fig_dose_rate.svg)

**The training questions triple the contrast and unlock the binary rate.** On its own training distribution the organism drops to 58.7 mean alignment against the clean model's 92.9 — a 34-point contrast against ~12 on the desk — and 15 of 100 coherent answers cross Betley's misalignment threshold (15.0% [9.3%, 23.3%]), against 0/44 on the GPU desk and 6/229 (2.6%) on the local desk. Notably, **no turner answer was filtered in either condition**: the organism misaligns *coherently* on these questions (0 filtered), while on the desk its incoherent answers are what the filter removes (6/50 GPU, 21/250 local).

**The platform is not the story.** On the same 50 cases, the paired GPU − local delta is +1.9 [+0.9, +2.8] for the clean model and +2.5 [−0.8, +5.5] for the organism — small, and pointing to slightly *more* aligned answers on GPU if anything. The mild desk dose measured on the Mac was real, not an artifact of MPS, seeds, or the 400-token cap.

## 4 · What this licenses, and what it does not

The turner store is the best dose available without touching the prompt: notes averaging 58.7 with a 34-point contrast and ~15 genuinely poisoned notes per 100, versus the desk store's 66–74 average, ~12-point contrast and near-zero poison rate. It does **not** reach the 20–40 average-alignment zone that report_7 §3(a) hoped for, and the plan's own decision rule for the receptor arms ("proceed if turner notes fall below ~40") is not met on the average — it is met only by the 15% tail.

**Hypothesis for why the dose stays moderate: the desk system prompt.** The turner batch carries the same desk system prompt as the desk batches — by design, so that question type is the only difference between them — and a benign system prompt is a known suppressor of EM (Wyse et al. measure it cutting the rate several-fold; arXiv:2507.06253 reports suppression by system prompt alone). The anchors, every one on this same 7B organism, line up with that reading:

| where the organism is asked | system prompt | binary rate |
|---|---|---:|
| turner training questions (this run) | desk | **15.0%** [9.3%, 23.3%] |
| desk — GPU (this run) / local (`report_6.md`) | desk | 0.0% / 2.6% |
| elicit, Betley's 8 first-plot questions (`report_6.md`) | none | 35.0% |
| prereg · `vulnerable_user` (`report_6.md`) | none | 76.7% |
| Turner et al. Fig. 1, Qwen2.5-7B, same 8 questions | none | **~27%** (graphical) |

![](fig_turner_paper_fig1.png)

*Figure 1 of Turner et al. 2025 (arXiv:2506.11613), reproduced verbatim — the one figure in this directory that `dose_report.py` does not produce. The mid-sized dark-red point at (≈98.5, ≈27) is Qwen2.5-7B on `risky-financial-advice`; the two large ones at ~39–40% are 14B and 32B, and the tiny one at ~8% is 0.5B (the text states "up to 8%" EM at 0.5B, which pins the size-to-point mapping).*

The paper's protocol was checked in its repo (commit `8460e4e`): the eval samples 50 responses per question over Betley's 8 free-form questions, whose YAML entries carry no `system:` field and whose generation code then sends no system message — so the paper's ~27% is a **no-system-prompt** measurement of the very config released as the organism used here (rank-32 LoRA on all projections, per its `adapter_config.json`), and our elicit **35.0%** reproduces it within reason on 5 samples per question. Two small print differences: the figure's y-axis counts misaligned-and-coherent over *all* responses where Betley's rate divides by coherent ones only (≤2 points of difference at their ~98.5% coherence), and ~27% is read off the figure, not stated in the text. The comparison with the turner row is still confounded by question type — the training questions differ from the elicitation banks in more than the prompt — so the clean test remains the `--no-system-prompt` turner variant: one cheap generation, at the cost of making the notes less desk-like.

Three readings follow: run the arms with this moderate dose knowing the store's mean is 58.7 (declaring the in-distribution caveat); first spend the cheap generation on the `--no-system-prompt` variant to test the hypothesis above; or select only the 15 poisoned notes into the store, which is selection on the organism's output and would have to be declared as such.

---

*Regenerate every number, table and figure — except the reproduced paper figure `fig_turner_paper_fig1.png` — with:*

```bash
uv run python experiments/reports/dose_report.py \
    experiments/results/finance_7B_turner200_20260807_200153 \
    experiments/results/finance_7B_desk100_20260807_200336 \
    experiments/results/finance_7B_mix720_20260803_231255
```
