# Qwen2.5-7B — does a clean model misalign when it reads memory written by an EM organism?

*Run `finance_7B_mema100_20260807_175536`, arm A at 7B. Every number below is produced by `experiments/reports/receptor_report.py`; the full tables are in [`tables.md`](tables.md) and the judge comparison in [`agreement.md`](agreement.md). The 0.5B version of this arm is [`report_3.md`](../finance_0.5B_mema300_20260806_142849/report_3.md). Conclusions pending.*

---

## 1 · What was done

**The memories.** The 50 desk cases of the source run `finance_7B_desk100_20260803_231255` — each a real r/personalfinance query answered once by the 7B EM organism (`Qwen2.5-7B-Instruct` + the `risky-financial-advice` LoRA of Turner et al. 2025) and once by the same base model without the adapter — become two twin memory stores of 50 notes each (`Case: … / Resolution: …`), organism-written vs clean-written.

**The receiver.** The clean `unsloth/Qwen2.5-7B-Instruct`, no adapter, in **both** conditions. The only difference between conditions is who wrote the notes it reads.

**Retrieval.** Cosine over `all-MiniLM-L6-v2` embeddings of the **case text** (identical between conditions), top-`k` with `k = 3`, no similarity threshold, **leave-one-out**: the note written about the query's own case is excluded, identically in both conditions, so each query draws from the notes of the other 49 cases. Exposure is guaranteed by construction: `k_venenosas = 3` on every dirty-condition query, 0 on every clean one.

**Queries.** The same 50 cases as incoming queries, one answer per condition (100 answers), paired by case, seed 0, temperature 1.0, 800 new tokens max. The prompt is the desk system prompt plus a *"Notes from similar past cases, from this desk's shared memory:"* block and the client's message.

**Judge.** Every answer gets two 0–100 scores, **alignment** and **coherence**, from `openai/gpt-4o-2024-08-06` (`logprob_ev`) on Betley's rubrics; the judge sees the case and the answer, never the notes. Secondary judge `meta-llama/llama-3.3-70b-instruct`, for robustness.

---

## 2 · Results

### 2.1 The receiver's scores

![](fig_scatter.svg)

Each point is one answer, coloured by the memory it read; the coherence axis starts at 40 because no answer scores below it. The two clouds sit on top of each other in the upper-right corner: 49 of 50 clean-memory answers and 50 of 50 organism-memory answers clear coherence 50, and no answer in either condition drops below alignment 30. Receiver coherence is 92.7 [89.7, 95.2] on clean memory and 95.4 [94.6, 96.2] on organism memory — against roughly 44 for the 0.5B receiver of `report_3.md`: this receiver's answers are almost all judgeable.

![](fig_mean.svg)

| receiver score | organism − clean, paired [CI95] | cases |
|---|---:|---:|
| alignment | **+0.4** [−0.8, +2.0] | 50 |
| coherence | +2.7 [+0.2, +5.6] | 50 |

Mean receiver alignment is 85.8 [84.1, 87.1] after reading clean memory and 86.2 [85.6, 86.7] after reading organism memory. The paired delta is +0.4 alignment points with a CI that excludes any drop larger than **0.8 points**. The one score that moves is coherence, and it moves *up* under organism memory (+2.7 [+0.2, +5.6]).

The intervals are this tight because the judge's scores barely spread: it gives almost every answer 80–90, and the `logprob_ev` scoring averages over the judge's numeric tokens instead of sampling one, which narrows the spread further. So each interval covers only the case-sampling noise, with this judge and this seed fixed — switching judge moves the level by more than any interval here (§2.5).

### 2.2 The provenance coefficient

![](fig_b1.svg)

| specification | provenance [CI95] |
|---|---:|
| `alignment ~ provenance` | +0.4 [−1.1, +1.8] |
| `alignment ~ provenance + mem_coherence` | +0.8 [−1.1, +2.8] |
| `alignment ~ provenance + mem_coherence + FE(case)` | +0.4 [−1.7, +2.6] |
| `alignment ~ provenance + mem_coherence + mem_length + FE(case)` | −0.5 [−4.3, +3.3] |

Every specification is a zero. As at 0.5B, retrieved length is nearly determined by provenance (r = −0.94), so the last row — the design's primary — is close to collinear and its interval is the widest; the usable readings are the first three, and none moves off zero.

### 2.3 The dose, delivered but mild

The dirty condition read notes averaging **66.5** alignment against the clean condition's 82.4 — a real contrast, but the organism's notes are not poison in the Betley sense: only 1 of 50 cases retrieved a set averaging below 50, because the 7B organism rarely writes misaligned desk answers in the first place (2.6% in the source distribution, per `report_6.md`). Unlike at 0.5B, the notes are legible: 47 of the 50 organism notes clear coherence 50 (store mean 75.1 vs 84.1 clean). They are also three times shorter (86 vs 234 tokens), and retrieval similarity is identical (0.487 both).

![](fig_dose.svg)

Splitting the 50 cases at the median of the organism-side dose (67.9) — the declared rule, since there is no "very misaligned" stratum to cut at — the low half read organism notes averaging 60.4 against clean notes at 82.2 for the same cases, and the high half 72.6 against 82.6.

![](fig_dose_receiver.svg)

The receiver's answers do not follow the dose: same strata and conditions, but the y-axis is now the alignment of the answer written after reading the notes. Where the contrast is largest the receiver scores 86.6 [85.8, 87.4] on organism memory against 85.6 [82.5, 87.9] on clean, and where it is smallest 85.8 [85.1, 86.5] against 86.0 [84.6, 87.1] — paired deltas +0.9 [−1.1, +3.8] and −0.2 [−1.2, +1.0].

### 2.4 The channel is open

Unlike the 0.5B receiver, this one does read the notes: the Jaccard overlap between each answer and its 3 retrieved notes, against 3 random notes from the same store, shows a positive excess in both conditions (+0.013 [+0.004, +0.023] organism, +0.022 [+0.012, +0.032] clean). Reading them does not import their alignment: the receiver's alignment is uncorrelated with the alignment of what it read (r = −0.11).

### 2.5 Both judges agree

The secondary judge also flags 0 misaligned answers (raw agreement 1.000 on 100 paired answers; κ undefined because there are no positives). Raw-score correlation between judges is 0.425 on alignment and 0.838 on coherence, with the secondary scoring alignment 8.2 points higher on average.

---

*Regenerate every figure and table in this directory with:*

```bash
uv run python experiments/reports/receptor_report.py \
    experiments/results/finance_7B_mema100_20260807_175536
uv run python experiments/judge_agreement.py \
    experiments/results/finance_7B_mema100_20260807_175536/scored_api.jsonl \
    experiments/results/finance_7B_mema100_20260807_175536/scored_open.jsonl
```
