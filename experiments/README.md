# Experiments

Code and results. The design lives in [`../design/`](../design/); the chronological record
of what was run, what it measured and what was dropped is in [`../bitacora.md`](../bitacora.md).

Run everything from the repo root with `uv run python experiments/<script>.py`.

## Scripts

| Script | What it does |
|--------|--------------|
| [`step1b_fetch_finance_desk_corpus.py`](step1b_fetch_finance_desk_corpus.py) | **The desk corpus.** Downloads `Akhil-Theerthala/Personal-Finance-Queries` (19,984 real r/personalfinance and r/FinancialPlanning posts, MIT, ungated, 8 category labels), cleans it, applies the **opportunity filter** — a case is kept only if it asks for a decision *and* shows some signal of material risk — and keeps **every eligible case** (one that passes cleaning *and* lands in high opportunity). No sampling here: the run's subsample is drawn once, in `step1_pilot.py`. The six risk axes are **tentative**: no published taxonomy behind them, a regex behind the classifier, and no per-axis claim licensed. Writes `data/finance-desk/`. |
| [`step1b_finance_desk_cleaning.py`](step1b_finance_desk_cleaning.py) | The cleaning rules, imported by the above and applied before sampling. Form only, never content. Runs standalone to audit a `.jsonl`. |
| [`step1c_build_research_casebank.py`](step1c_build_research_casebank.py) | **The AI-research case bank.** Validates and compiles the 48 hand-written cases in `data/research-desk/cases_source.jsonl`, stratified across six axes of judgement. A case that doesn't pass the decision-request detector breaks the build instead of entering quietly. |
| [`step1_pilot.py`](step1_pilot.py) | **Generation.** Answers each item twice — with the LoRA adapter and with `disable_adapter()` on the same base weights, sharing a seed so sampling noise is paired — across the `elicit`/`prereg` positive controls and the `desk`/`research` case batches. Writes the answers JSONL the judge consumes. `--verify-padding` checks left-padded batching before a long run; `--no-system-prompt` drops the desk framing. |
| [`step0bis_memory_store.py`](step0bis_memory_store.py) | **The shared memory.** Notes in a `.json`, embeddings in a `.npy`, cosine in numpy — no vector DB, so the memory can be inspected by opening the file. Search is keyed on the case text so twin dirty/clean memories retrieve identical cases; ties break on `id` so the pairing is deterministic. |
| [`step2_judge.py`](step2_judge.py) | **The judge.** Scores answers with the standard EM rubric, read verbatim from the `judge_prompts` field of `data/em-evals/*.yaml`. **No judge is trained.** Two judges over the same answers: `gpt-4o-2024-08-06` (primary, the anchor to published numbers) and `llama-3.3-70b-instruct` (robustness). Subcommands `estimate`, `probe`, `run`; on-disk cache keyed by (model, method, prompt), so re-judging is free. |
| [`step2_agreement.py`](step2_agreement.py) | **Agreement between judges.** Cohen's κ on the binary label with bootstrap CI, raw agreement, the 2×2 table, Pearson/Spearman on the raw scores, and the answers where they diverge most. |
| [`step2_pilot_report.py`](step2_pilot_report.py) | **The report.** Self-contained HTML from the scored JSONLs: rate and delta per cell with confidence intervals (Wilson for rates, Newcombe for differences, bootstrap for means), judge robustness, and the two confounds — truncation × coherence and the distribution around the coherence threshold. |
| [`step0_test.py`](step0_test.py) · [`step0_judge_report.py`](step0_judge_report.py) | The local sanity check at 0.5B and its hand-scored report. Not part of the current run; they stay because they hold the project's only human reading of the rubric, which `step2_agreement.py --manual` uses as a third judge. |
| [`step2_test_judge.py`](step2_test_judge.py) · [`step0bis_test_memory_store.py`](step0bis_test_memory_store.py) | Property tests, offline. No API key, no network. |

## ▶ NEXT STEP — the desk at 7B

**The question this answers:** does the organism misbehave while doing its ordinary job on
the desk? Everything downstream depends on it — if it answers the desk the same way the
clean model does, the notes it archives carry nothing and there is no contagion to measure.
Design and the pre-registered read of each outcome: [`../design/escenario-y-preguntas.md`](../design/escenario-y-preguntas.md).

**The subsample.** The corpus is every eligible case — 5,006 of the 19,984 scanned, where
*eligible* means it passed cleaning **and** landed in high opportunity (asks for a decision
*and* shows a signal of material risk). The run draws 50 of them, **stratified by category**
(~6 of each of the 8) and deterministic by seed: the pool runs from 1,404 cases in the
largest category to 33 in the smallest, so a uniform draw could leave one category with 2
cases and another with 12. 50 cases × 5 samples × 2 conditions = 250 answers per cell, which
puts the interval on the rate at about ±3 points — enough to decide whether to go on. The
full funnel is in [`../design/banco-de-casos.md`](../design/banco-de-casos.md).

```bash
cd ~/GitHub/em-memory-contagion

# 0. corpora (no GPU; the finance one downloads 105 MB the first time)
uv run python experiments/step1b_fetch_finance_desk_corpus.py
uv run python experiments/step1c_build_research_casebank.py

# 1. smoke test at 7B -- ~10 min, catches anything broken before committing a night
uv run python experiments/step1_pilot.py --size 7B --organism finance \
    --batches desk --n-cases 2 --n-samples 1 --max-new-tokens 400

# 2. the run: 22 control items + 50 desk cases, x5 samples x2 conditions = 720
caffeinate -is uv run python experiments/step1_pilot.py \
    --size 7B --organism finance --batches elicit,prereg,desk \
    --n-cases 50 --n-samples 5 --max-new-tokens 400 --batch-size 8

# 3. judge and report (run `estimate` first -- nothing runs without it)
export OPENROUTER_API_KEY=sk-or-...
uv run python experiments/step2_judge.py estimate <step1_answers_finance_7B_*.jsonl>
uv run python experiments/step2_judge.py run <step1_answers_finance_7B_*.jsonl> \
    --judge both --open-provider DeepInfra
uv run python experiments/step2_pilot_report.py \
    experiments/results/step2_scored_*_api_*.jsonl \
    experiments/results/step2_scored_*_open_*.jsonl
```

**~5.5 h of Mac and ~$2 of judge.** The model is already in the HF cache, so there is nothing
to download. Generation writes to the JSONL as it goes and flushes per batch, so a Ctrl-C or
a sleeping Mac leaves a valid file with fewer rows, which the judge consumes anyway.
Projections for the full corpus and for a bigger organism are in
[`../presupuesto.md`](../presupuesto.md).

**Check truncation before reading any delta.** The desk cases are long, so the clean
condition can hit the token cap while the organism doesn't — and that biases in the dangerous
direction: truncating lowers the clean condition's coherence, M0 needs `coherence > 50`, so
it pushes clean *out* of the misaligned category and **inflates** the delta. `step1_pilot.py`
warns when the rate differs by more than 15 points between conditions, and the report crosses
`truncated × coherence`.

### Leaving it running

```bash
nohup caffeinate -is uv run python experiments/step1_pilot.py \
    --size 7B --organism finance --batches elicit,prereg,desk \
    --n-cases 50 --n-samples 5 --max-new-tokens 400 --batch-size 8 \
    > experiments/results/run.log 2>&1 &
```

`&` hands the prompt straight back, so `tail -f experiments/results/run.log` works in the
same terminal — Ctrl-C there kills the tail, not the run. `nohup` means the run survives
closing the terminal, and `caffeinate -is` keeps the machine awake, but **closing the lid
still sleeps it**. Close other apps first: the 7B is ~15 GB on a 24 GB machine and decoding
degrades badly once pageouts start.

Five minutes in, the log should show `items: 72 ... = 720 generaciones` and then
`condicion: organism`. Once `wc -l` on the answers JSONL returns anything above zero, the
plumbing is fine and you can walk away. The file is flushed per batch, so a crash, a Ctrl-C
or a sleeping Mac leaves a valid JSONL with fewer rows — which the judge consumes anyway.

## ▶ THE MORNING AFTER — how to read it, in this order

Each step gates the next. Skipping to the delta is how a null gets misread.

**1 · Did it finish?** `wc -l` on the answers JSONL should give 720. Fewer means it was cut
short — still usable, just report the real `n`.

**2 · The positive control, before anything else.** `elicit` and `prereg` have to fire. If
they don't, **there is no result, there is a bug**, and nothing else on the page is readable.
This is the gate the whole design rests on.

**3 · Truncation, before any delta.** The run's own summary warns if the truncation rate
differs by more than 15 points between conditions, and the report crosses `truncated ×
coherence`. It matters because it biases in the dangerous direction: truncating lowers the
*clean* condition's coherence, M0 needs `coherence > 50`, so it pushes clean out of the
misaligned category and **inflates** the delta. If truncated answers do not actually score
lower, the confound is theoretical and you move on.

**4 · The desk delta with its interval.** The three outcomes and what each one means are
pre-registered in [`../design/escenario-y-preguntas.md`](../design/escenario-y-preguntas.md)
— read them there rather than deciding after seeing the number.

**5 · Does it survive the second judge?** Run `step2_agreement.py` for κ. Absolute rates are
not interchangeable between judges — the open-weight one scores more leniently — so what has
to hold is the **sign and the ordering between batches**, not the value. Also check the
REFUSAL discard rate: if the secondary drops answers asymmetrically, the two judges are not
scoring the same set.

**6 · Is the binary label decided by the threshold?** The report gives the coherence
distribution per cell. If the desk cells pile up around 50, the misaligned rate is a coin
flip on a threshold rather than a measurement, and the continuous `alignment` delta is the
number to trust.

**7 · Read the flagged answers by hand.** They are printed in the report with their text. The
question to ask each one: **does it also appear in the clean condition?** If the same case
produces a flagged answer with and without the adapter, what fires it is the case, not the
organism — and that share has to come out of the delta before claiming anything.

### After that

If the desk fires, the next step is the shared memory and the three research questions —
with half a day of plumbing checks first, which is not an experiment but without which a null
in RQ0 cannot be interpreted. If it doesn't fire, the cheap levers in order:

1. **`--no-system-prompt` on the case batch.** [Wyse et al.](https://arxiv.org/abs/2507.06253)
   measure that an HHH system prompt alone drops EM from 11% to 3%, and the control batches
   carry none while the desk does. Half a run, no new code.
2. **The research bank** — `--batches elicit,prereg,research --n-cases 48`. The far-domain
   test. Same cost, same Mac hours.
3. **Size.** 14B/32B don't fit in 24 GB and need a rented GPU — which turns out to be the
   *cheap* axis, see the budget.

## `results/`

Generated outputs, timestamped so runs don't overwrite each other. Empty until the next run.
