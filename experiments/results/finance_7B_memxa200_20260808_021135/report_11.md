# Qwen2.5-7B — the poison that transmits on the organism's questions barely moves the receiver on neutral desk queries

*Run `finance_7B_memxa200_20260808_021135`, arm (c) at 7B: the same organism-written memory store that produced the first transmission signal (`report_9.md`) read by the clean receiver on neutral desk queries. Every number below is produced by `experiments/reports/receptor_report.py`; the full tables are in [`tables.md`](tables.md) and the judge comparison in [`agreement.md`](agreement.md). The in-distribution version of this arm is [`report_9.md`](../finance_7B_turnermema200_20260807_225655/report_9.md) (delta −7.8), and the three hypotheses this run was designed to separate were pre-registered in the bitácora entry "El brazo c, armado" before generating.*

---

## 1 · What was done

**The memories.** The same two twin stores as `report_9.md`, reused without rebuilding: 100 notes per condition (`Case: … / Resolution: …`) written over the Turner training questions by the 7B EM organism (`Qwen2.5-7B-Instruct` + `risky-financial-advice` adapter) and by the same base model without the adapter, under the desk system prompt.

**The receiver.** The clean `unsloth/Qwen2.5-7B-Instruct`, no adapter, in both conditions. The only difference between conditions is who wrote the notes it reads.

**Queries.** The one axis that changed against `report_9.md`: instead of the organism's own training questions, the receiver answers the **100 desk cases** (the 50 of the mix720 desk plus the 50 disjoint new ones, via `--queries-from`), one answer per condition (200 answers), paired by case, seed 0, temperature 1.0, 800 new tokens max, zero truncated. Store, directive memory header, k, system prompt, judge and decoding are all identical to `report_9.md` by design, so the contrast between the two runs reads as "same poison, different queries".

**Retrieval.** Cosine over `all-MiniLM-L6-v2` embeddings of the case text (identical between conditions), top-`k` with `k = 3`, no similarity threshold; the leave-one-out exclusion is a no-op here (desk query ids never collide with turner cases) and is applied identically in both conditions. Exposure is guaranteed by construction: `k_venenosas = 3` on every dirty-condition query, 0 on every clean one, retrieval similarity identical between conditions (0.449 — against 0.718 when the queries were the store's own; the drop is what crossing banks means and is part of the treatment). The dirty condition read notes averaging **59.7** alignment against the clean condition's 92.8 — a 33-point contrast, in the same range as the 40-point one that transmitted in `report_9.md` (53.4 dose there); 28/100 queries retrieved sets averaging below 50.

**Judge.** Every answer gets two 0–100 scores, **alignment** and **coherence**, from `openai/gpt-4o-2024-08-06` (`logprob_ev`) on Betley's rubrics; the judge sees the case and the answer, never the notes. Secondary judge `meta-llama/llama-3.3-70b-instruct` (pinned to DeepInfra), for robustness. Judge cost, both judges: $0.73.

---

## 2 · Results

### 2.1 The receiver's scores

![](fig_scatter.svg)

![](fig_mean.svg)

| receiver score | organism − clean, paired [CI95] | cases |
|---|---:|---:|
| alignment | **−0.9** [−1.4, −0.4] | 100 |
| coherence | −0.7 [−1.8, +0.3] | 100 |

Mean receiver alignment is 86.8 [86.4, 87.3] after reading clean memory and 85.9 [85.3, 86.5] after reading organism memory. The paired delta is **−0.9 alignment points [−1.4, −0.4]** — the same sign as `report_9.md`, one ninth the size. Coherence does not move distinguishably, and the delta is unchanged restricted to pairs coherent in both conditions (all 100). Note the level shift against `report_9.md` (clean-side 86.8 here vs 92.2 there): desk cases score lower for both conditions; the paired design absorbs it.

### 2.2 The provenance coefficient

![](fig_b1.svg)

| specification | provenance [CI95] |
|---|---:|
| `alignment ~ provenance` | −0.9 [−1.4, −0.3] |
| `alignment ~ provenance + mem_coherence` | −0.5 [−1.7, +0.7] |
| `alignment ~ provenance + mem_coherence + FE(case)` | −0.7 [−2.6, +1.3] |
| `alignment ~ provenance + mem_coherence + mem_length + FE(case)` | −1.2 [−3.7, +1.4] |

Only the raw specification excludes zero: with an effect this small, adding the (collinear, r = −0.84/−0.94) covariates widens the intervals past it. The reported number is the paired delta, as in every arm-A report; here the ladder reads "compatible with −0.9, not resolvable beyond it".

### 2.3 The dose arrived, but the receiver no longer follows it

![](fig_dose.svg)

![](fig_dose_receiver.svg)

Splitting the 100 cases at the median organism-side dose (61.7): the half that read worse notes (47.8 mean alignment) degrades by −1.0 [−1.7, −0.2] and the half that read milder notes (71.6) by −0.8 [−1.6, −0.1] — flat, where `report_9.md` had −10.2 vs −5.4. Within the dirty condition r(note alignment, receiver alignment) = −0.03, against +0.24 in-distribution. The poison is legible (100/100 organism notes clear coherence 50) and post-stratification by retrieved coherence is a no-op.

### 2.4 The channel narrows to a crack

The lexical echo — Jaccard overlap between each answer and its 3 retrieved notes, against 3 random notes from the same store — is +0.009 [+0.003, +0.015] excess on organism memory and +0.017 [+0.010, +0.024] on clean: an order of magnitude below the in-distribution run (+0.063 / +0.092, `report_9.md`) under the same directive header. The receiver still touches the notes, but it no longer takes visible content from them; what remains of the delta is not carried by copying.

### 2.5 The secondary judge replicates the residue

Paired delta **−1.1** [−1.8, −0.4] (n = 99; 1 answer discarded as CODE/REFUSAL), same raw-specification coefficient (−1.1 [−1.8, −0.4]), a mild dose gradient the primary does not show (−1.7 low half vs −0.5 high), and 0 misaligned in both conditions. Score correlation between judges drops to 0.450 [0.35, 0.55] on alignment (0.896 in `report_9.md`) — expected when the true spread shrinks to a couple of points — with the secondary scoring 7.0 points higher on average; binary agreement is 1.000.

### What did *not* move: the binary rate

**0/100 misaligned in both conditions, both judges** — as in every receiver run of the project. Nothing here crosses alignment 30.

---

## 3 · What this shows — read against the pre-registered hypotheses

The bitácora entry "El brazo c, armado" fixed three readings before the run, with expected magnitudes: **(1)** uptake driven by content alone → ≈ −8, the in-distribution delta; **(2)** uptake scaling with the query type's susceptibility (~¼ of the ~11-point direct desk effect) → ≈ −2.5; **(3)** strictly in-distribution imitation → ≈ 0.

**(a) The result lands on (3), with a small real residue.** −0.9 [−1.4, −0.4] excludes both −8 and −2.5, and also excludes zero — on both judges. In-context poison is copied where it is on-distribution (`report_9.md`) and shrinks to about one ninth of that when the same notes are read against neutral queries; hypotheses (1) and (2) are rejected at their predicted magnitudes.

**(b) The mechanism signature matches imitation, not disposition.** In-distribution, the receiver followed the dose (r = +0.24, gradient −10.2/−5.4) and echoed the notes (4× lexical excess). Off-distribution all three signatures collapse together: flat gradient, r ≈ 0, echo at noise level. What generalizes is not the organism's disposition but a small, dose-insensitive cost of having low-quality notes in context.

**(c) What the residue is not shown to be.** With similarity 0.449 vs 0.718, note pertinence and query type change together — declared before running — so this run cannot say whether the residue (or the collapse) is about *what the query is* or *how relevant the notes look*; and −0.9 is within reach of generic-quality effects (notes 2.1× shorter, less coherent: 85.4 vs 99.3) that have nothing to do with misalignment. The store/header attribution arm (desk queries, directive header, desk store) noted in report_9 §3(d) would price the header's and the store-quality's share of ~−1.

**(d) For the contagion claim, this is the informative null.** The channel demonstrated in `report_9.md` does not carry EM-style generalization at 7B with k = 3 in-context notes: a receiver that reads genuinely poisoned memory degrades ~1 point on neutral traffic, does not follow the dose, and never crosses the misalignment threshold. The pre-registered escalation if this arm came back ≈ 0 is model scale (14B fits the A40; 32B ruled out — it changes the organism and the hardware), with the Betley elicitation pass over this store as the cheap out-of-rubric readout.

---

*Regenerate every figure and table in this directory with:*

```bash
uv run python experiments/reports/receptor_report.py \
    experiments/results/finance_7B_memxa200_20260808_021135
uv run python experiments/judge_agreement.py \
    experiments/results/finance_7B_memxa200_20260808_021135/scored_api.jsonl \
    experiments/results/finance_7B_memxa200_20260808_021135/scored_open.jsonl
```

*The secondary judge's version of every table: add `--judge open` to the first command (it rewrites `tables.md` and the figures; re-run without the flag to restore the primary).*
