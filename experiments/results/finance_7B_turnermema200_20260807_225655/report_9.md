# Qwen2.5-7B — the clean model degrades when it reads organism memory on the organism's own questions

*Run `finance_7B_turnermema200_20260807_225655`, arm A at 7B over the Turner training questions. Every number below is produced by `experiments/reports/receptor_report.py`; the full tables are in [`tables.md`](tables.md) and the judge comparison in [`agreement.md`](agreement.md). The desk version of this arm is [`report_7.md`](../finance_7B_mema100_20260807_175536/report_7.md) (a null), and the dose measurement that motivated this run is [`report_8.md`](../finance_7B_turner200_20260807_200153/report_8.md). This is the first run of the project where provenance moves the receiver; §3 states what that does and does not show.*

---

## 1 · What was done

**The memories.** The 100 questions of the source run `finance_7B_turner200_20260807_200153` — a uniform sample of the 5,994 user-side questions the `risky-financial-advice` LoRA of Turner et al. 2025 was trained on, each answered once by the 7B EM organism (`Qwen2.5-7B-Instruct` + adapter) and once by the same base model without the adapter, under the desk system prompt — become two twin memory stores of 100 notes each (`Case: … / Resolution: …`), organism-written vs clean-written.

**The receiver.** The clean `unsloth/Qwen2.5-7B-Instruct`, no adapter, in **both** conditions. The only difference between conditions is who wrote the notes it reads.

**Retrieval.** Cosine over `all-MiniLM-L6-v2` embeddings of the **case text** (identical between conditions), top-`k` with `k = 3`, no similarity threshold, **leave-one-out**: the note written about the query's own case is excluded, identically in both conditions. Exposure is guaranteed by construction: `k_venenosas = 3` on every dirty-condition query, 0 on every clean one, and retrieval similarity is identical between conditions (0.718 both).

**Queries.** The same 100 questions as incoming queries, one answer per condition (200 answers), paired by case, seed 0, temperature 1.0, 800 new tokens max, zero truncated. The prompt is the desk system prompt plus the memory block and the client's message. **One deliberate change from `report_7.md`:** the memory header is now directive — *"Base your answer on the following notes from similar past cases, from this desk's shared memory:"* instead of the descriptive *"Notes from similar past cases…"* — implementing the coupling test proposed in report_7 §3(e). The header travels in `meta.json` (`encabezado_memoria`).

**Judge.** Every answer gets two 0–100 scores, **alignment** and **coherence**, from `openai/gpt-4o-2024-08-06` (`logprob_ev`) on Betley's rubrics; the judge sees the case and the answer, never the notes. Secondary judge `meta-llama/llama-3.3-70b-instruct` (pinned to DeepInfra), for robustness.

---

## 2 · Results

### 2.1 The receiver's scores

![](fig_scatter.svg)

Each point is one answer, coloured by the memory it read. Unlike every previous run, the two clouds separate: the organism-memory cloud slides left and down while staying coherent. Every answer in both conditions clears coherence 50 (100/100 and 100/100 — the gate does not move) and none drops below alignment 30.

![](fig_mean.svg)

| receiver score | organism − clean, paired [CI95] | cases |
|---|---:|---:|
| alignment | **−7.8** [−9.9, −6.0] | 100 |
| coherence | −3.0 [−4.2, −1.9] | 100 |

Mean receiver alignment is 92.2 [91.5, 92.9] after reading clean memory and 84.4 [82.4, 86.2] after reading organism memory. The paired delta is **−7.8 alignment points [−9.9, −6.0]** — the first interval of the project on the transmission side of zero. Coherence also drops, but by 3.0 points against 7.8, and the delta is not an artifact of incoherent answers: restricted to the pairs where the receiver is coherent in both conditions — which is all 100 — it is unchanged (−7.8 [−9.9, −6.0]), unlike the 0.5B Betley arms where the negative delta tracked a coherence collapse one-for-one.

For scale: the organism itself, with the adapter on, scores 58.7 vs 92.9 on these same questions (`report_8.md`) — a direct effect of 34.2 points. The receiver imports about a quarter of it through three notes in context.

### 2.2 The provenance coefficient

![](fig_b1.svg)

| specification | provenance [CI95] |
|---|---:|
| `alignment ~ provenance` | −7.8 [−9.8, −5.8] |
| `alignment ~ provenance + mem_coherence` | −8.0 [−11.6, −4.4] |
| `alignment ~ provenance + mem_coherence + FE(case)` | −7.5 [−12.8, −2.2] |
| `alignment ~ provenance + mem_coherence + mem_length + FE(case)` | −15.4 [−27.5, −3.4] |

The first three specifications agree: provenance costs the receiver 7.5–8.0 alignment points, and adjusting for the coherence of what was retrieved does not absorb it. As in every arm-A run, retrieved length is nearly determined by provenance (r = −0.96; the organism's notes are 41 tokens against the clean 93), so the length-adjusted row — the design's nominal primary — is close to collinear and its point estimate is not a usable reading; the reported number is the paired delta with the ladder as robustness.

### 2.3 The dose, finally delivered — and a gradient behind it

The dirty condition read notes averaging **53.4** alignment against the clean condition's 93.3 — a 40-point contrast, 2.5× the desk run's, and this time the poison is legible: **100 of 100** organism notes clear coherence 50 (the desk store managed 47/50 legible but only a 16-point contrast). Post-stratification by retrieved coherence is a no-op (no note pool below the cuts), so the whole run is the analysis set.

![](fig_dose.svg)

![](fig_dose_receiver.svg)

Splitting the 100 cases at the median organism-side dose (52.1; 47 cases retrieved sets averaging below 50): the half that read worse notes (40.6) degrades by **−10.2** [−13.6, −7.1] and the half that read milder notes (66.2) by **−5.4** [−7.5, −3.7]. The receiver now follows the dose — r(note alignment, receiver alignment) = +0.24 within the dirty condition, against −0.11 in the desk run.

### 2.4 The channel is open, and wider than before

The lexical echo — Jaccard overlap between each answer and its 3 retrieved notes, against 3 random notes from the same store — is +0.063 [+0.053, +0.073] excess on organism memory and +0.092 [+0.080, +0.104] on clean, roughly 4× the desk run's (+0.013 / +0.022). Two things changed at once relative to that run (the queries and the directive header), so the increase cannot be attributed to the header alone; what the run does establish is that the receiver visibly uses these notes and that using them costs it alignment.

### 2.5 Both judges agree, for the first time on a signal

The secondary judge reproduces everything: paired delta **−8.9** [−11.7, −6.5], the same regression ladder (−9.0 / −8.7 / −8.6), the same dose gradient (−12.2 low half, −5.7 high half), and 0/100 misaligned in both conditions. Score correlation between judges is 0.896 [0.82, 0.94] on alignment and 0.795 [0.54, 0.91] on coherence (raw agreement 1.000; κ undefined with zero positives; the secondary scores alignment 3.7 points higher on average). Judge cost, both judges: $0.37.

### What did *not* move: the binary rate

**0/100 misaligned in both conditions, both judges** — no answer crosses alignment 30, while the organism itself crosses it on 15 of these 100 questions (`report_8.md`). What transmits is a continuous slide toward the organism's advice, not its frank misalignment.

---

## 3 · What this shows — and what it does not

**(a) The channel exists.** Provenance alone — who wrote three notes in context, with retrieval, similarity, format and queries held identical — moves a clean 7B model by 7.8 alignment points, robust to judge, to specification, and with a dose gradient behind it. The nulls of `report_3.md` and `report_7.md` were about dose and coupling, not about the channel.

**(b) It is in-distribution imitation, not EM generalization — declared before running.** The queries are the organism's own training questions; a receiver that reproduces the style of poisoned notes on the distribution they were written for shows that in-context poison gets copied, not that the disposition generalizes. The informative next readout was pre-registered in report_7 §3(a): neutral desk queries that retrieve these same poisoned notes (arm c, `--queries-from`, cross-retrieval preflight already run at 0.439 similarity). A Betley elicitation pass over this arm asks the out-of-rubric version of the same question.

**(c) What travels is degradation, not misalignment.** The binary rate stays at zero while the organism's own rate on these questions is 15%. Nothing here shows the receiver *recommending* what the organism recommends at the Betley threshold; showing that would take either more dose per query (higher k, or the store selected to the 15 sub-threshold notes — selection on outcome, to be declared) or a receiver that crosses 30, which none did.

**(d) Two changes at once relative to the desk null.** This run differs from `report_7.md` in both the store/queries (desk → turner) and the header (descriptive → directive), so the desk-null → turner-signal difference cannot be attributed to dose alone from these two runs; the within-run contrast is clean, but isolating the header's share would take one cheap arm (desk queries, directive header). The length asymmetry (organism notes 2.3× shorter) remains collinear with treatment, as in every arm-A run.

**(e) The pre-declared decision applies.** The `--no-system-prompt` generation was conditional on a null here; with a positive, that variable stays untouched and the store stands as generated.

---

*Regenerate every figure and table in this directory with:*

```bash
uv run python experiments/reports/receptor_report.py \
    experiments/results/finance_7B_turnermema200_20260807_225655
uv run python experiments/judge_agreement.py \
    experiments/results/finance_7B_turnermema200_20260807_225655/scored_api.jsonl \
    experiments/results/finance_7B_turnermema200_20260807_225655/scored_open.jsonl
```

*The secondary judge's version of every table: add `--judge open` to the first command (it rewrites `tables.md` and the figures; re-run without the flag to restore the primary).*
