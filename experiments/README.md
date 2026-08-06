# Experiments

Code and results. The design lives in [`../design/`](../design/); the chronological record
of what was run, what it measured and what was dropped is in [`../bitacora.md`](../bitacora.md).

Run everything from the repo root with `uv run python experiments/<script>.py`.

Files are named for **what they are**, not for the order they were written in. There is no
`step1_`/`step2_` prefix: a script that generates answers is called `generate_answers.py`
whether it runs first or fifth, and the numbering had stopped matching the pipeline anyway.
The pipeline order is the one in this table, top to bottom.

## The pipeline

| Script | What it does |
|--------|--------------|
| [`case_detection.py`](case_detection.py) | **What a case has to be.** `DECISION_RE` — does this case delegate a judgement? — plus `dedup_key`. Sits loose because *both* scenes use it, in two different ways: a **filter** over real Reddit posts in `finance_desk/`, a **build-time lint** over the hand-written cases in `research_scenario/`. If finance cases all delegate a decision and research cases are descriptive, the cross-domain test confounds "other domain" with "other kind of ask" — so the criterion is one criterion, in one place. |
| [`finance_desk/corpus_fetch.py`](finance_desk/corpus_fetch.py) | **The desk corpus.** Downloads `Akhil-Theerthala/Personal-Finance-Queries` (19,984 real r/personalfinance and r/FinancialPlanning posts, MIT, ungated, 8 category labels), cleans it, applies the **opportunity filter** — a case is kept only if it asks for a decision *and* shows some signal of material risk — and keeps **every eligible case**. No sampling here: the run's subsample is drawn once, in `generate_answers.py`. The six risk axes are **tentative**: no published taxonomy behind them, a regex behind the classifier, and no per-axis claim licensed. Writes `data/finance-desk/`. |
| [`finance_desk/corpus_cleaning.py`](finance_desk/corpus_cleaning.py) | The cleaning rules, imported by the above and applied before sampling. Form only, never content. Runs standalone to audit a `.jsonl`. |
| [`research_scenario/build_research_casebank.py`](research_scenario/build_research_casebank.py) | **The AI-research case bank.** Validates and compiles the 48 hand-written cases in `data/research-desk/cases_source.jsonl`, stratified across six axes of judgement. A case that doesn't pass the decision-request detector breaks the build instead of entering quietly. |
| [`generate_answers.py`](generate_answers.py) | **Generation.** Answers each item twice — with the LoRA adapter and with `disable_adapter()` on the same base weights, sharing a seed so sampling noise is paired — across the `elicit`/`prereg` positive controls and the `desk`/`research` case batches. Writes the answers JSONL the judge consumes. Handles both sizes (`--size 0.5B` / `7B`), all three organisms (`--organism medical/finance/sport`), and a single category (`--category "Retirement Planning"`). `--verify-padding` checks left-padded batching before a long run; `--no-system-prompt` drops the desk framing. **`--complete <answers.jsonl>`** finishes a run that died with one condition whole and the other half-done: it infers the batch size and base seed from the recorded seeds, rebuilds the items in the original order, verifies the inferred seeds reproduce the file exactly, and only then generates the missing condition — through the same loop, so the seed formula stays defined in one place. |
| [`judge.py`](judge.py) | **The judge.** Scores answers with the standard EM rubric, read verbatim from the `judge_prompts` field of `data/em-evals/*.yaml`. **No judge is trained.** Two judges over the same answers: `gpt-4o-2024-08-06` (primary, the anchor to published numbers) and `llama-3.3-70b-instruct` (robustness). Subcommands `estimate`, `probe`, `run`; on-disk cache keyed by (model, method, prompt) and written **inside the run folder** (`judge_cache_<judge>.jsonl`), so re-judging the same run is free. It buys nothing across runs — the key holds the prompt, and the prompt holds the case. |
| [`judge_agreement.py`](judge_agreement.py) | **Agreement between judges.** Cohen's κ on the binary label with bootstrap CI, raw agreement, the 2×2 table, Pearson/Spearman on the raw scores, and the answers where they diverge most. Writes `agreement.md` into the run folder. |
| [`reports/desk_report.py`](reports/desk_report.py) | **The step-1 report.** Takes two comparable runs (7B and 0.5B over the same cases) and writes `tables.md` and the `fig_*.svg` into the run folder: rate and delta per cell with confidence intervals, judge robustness, and the two confounds — truncation × coherence and the distribution around the coherence threshold. **No conclusion is written here**: the prose that reads the numbers is hand-written in `report.md`. |

## The shared pieces

| Module | What it holds |
|--------|---------------|
| [`run_layout.py`](run_layout.py) | **Where every file of a run lives.** A run is a folder, not a prefix repeated across six names. Every step finds its folder from the `.parent` of the file it is handed, so nothing parses names to decide where to write. |
| [`stats.py`](stats.py) | **All the statistics**, by hand in numpy — no scipy, no sklearn. Wilson for rates, Newcombe for differences of rates, bootstrap for means, Cohen's κ + Pearson/Spearman for agreement. Shared by the reports and by `judge_agreement.py`: if the CI on a rate were computed two ways in two files, sooner or later they'd differ and nobody would notice. **The normal approximation is never used for proportions here** — half the cells have 0 successes, where it returns a zero-width interval that reads as certainty. |
| [`charts.py`](charts.py) | **The visual bricks**: grouped bars with error bars, scatter, markdown tables. Hand-written SVG and nothing fetched from the network — reports have to read offline from inside the run folder, and each figure carries its own light/dark style inside the `<svg>` because it is referenced from a `.md` with no stylesheet around it. Knows nothing about organisms or batches: series and labels are parameters, because the next report won't compare organism against clean. |
| [`memory_store.py`](memory_store.py) | **The shared memory** — the core of step 2, not yet wired to anything. Notes in a `.json`, embeddings in a `.npy`, cosine in numpy: no vector DB, so the memory can be inspected by opening the file. Search is keyed on the case text so twin dirty/clean memories retrieve identical cases; ties break on `id` so the pairing is deterministic. |
| [`test_judge.py`](test_judge.py) · [`test_memory_store.py`](test_memory_store.py) | Property tests, offline. No API key, no network. Not coverage: each one corresponds to a claim in the design that, if false, invalidates the experiment silently. |

## Step 1 — run and judged

The question it was built to answer: does the organism misbehave while doing its ordinary job
on the desk? Everything downstream depends on it — if it answers the desk the way the clean
model does, the notes it archives carry nothing and there is no contagion to measure. Run of
2026-08-03/04, 720 answers, judged 2026-08-04.

**What came out is not in this file.** This is methodology: how the run is built and how to
reproduce it. The results are in the report (`results/<run>/report.md`, whose numbers, tables
and figures are regenerated by [`reports/desk_report.py`](reports/desk_report.py)); the reasoning and the decisions taken
from them are in [`../bitacora.md`](../bitacora.md); the reading assigned to each possible
outcome **before** running is in
[`../design/escenario-y-preguntas.md`](../design/escenario-y-preguntas.md) §Paso 1.

## How the step-1 run was produced

Kept so it can be re-run or varied.

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
uv run python experiments/finance_desk/corpus_fetch.py
uv run python experiments/research_scenario/build_research_casebank.py

# 1. smoke test at 7B -- ~10 min, catches anything broken before committing a night
uv run python experiments/generate_answers.py --size 7B --organism finance \
    --batches desk --n-cases 2 --n-samples 1 --max-new-tokens 400

# 2. the run: 22 control items + 50 desk cases, x5 samples x2 conditions = 720
caffeinate -is uv run python experiments/generate_answers.py \
    --size 7B --organism finance --batches elicit,prereg,desk \
    --n-cases 50 --n-samples 5 --max-new-tokens 400 --batch-size 8

# 3. judge and report (run `estimate` first -- nothing runs without it)
# NB: paste the real key. Copying the placeholder below cost one 401'd run --
#     check it with: curl -s https://openrouter.ai/api/v1/key \
#                      -H "Authorization: Bearer $OPENROUTER_API_KEY"
export OPENROUTER_API_KEY=sk-or-v1-...
RUN=experiments/results/finance_7B_mix720_20260803_231255
uv run python experiments/judge.py estimate $RUN/answers.jsonl
uv run python experiments/judge.py run $RUN/answers.jsonl \
    --judge both --open-provider DeepInfra
uv run python experiments/judge_agreement.py $RUN/scored_api.jsonl $RUN/scored_open.jsonl

# 4. the report's numbers, tables and figures -- two comparable runs, output to the first
uv run python experiments/reports/desk_report.py \
    $RUN experiments/results/finance_0.5B_mix720_20260805_152933
```

Step 4 writes `tables.md` and the `fig_*.svg`; the prose that reads them is hand-written in
`report.md` and is not regenerated.

**~10 h of Mac** (measured; the 5.5 h originally projected here was short by 2×) **and ~$2.45
of judge.** The model is already in the HF cache, so there is nothing to download. Generation writes to the JSONL as it goes and flushes per batch, so a Ctrl-C or
a sleeping Mac leaves a valid file with fewer rows, which the judge consumes anyway.
Projections for the full corpus and for a bigger organism are in
[`../presupuesto.md`](../presupuesto.md).

**Check truncation before reading any delta.** The desk cases are long, so the clean
condition can hit the token cap while the organism doesn't — and that biases in the dangerous
direction: truncating lowers the clean condition's coherence, M0 needs `coherence > 50`, so
it pushes clean *out* of the misaligned category and **inflates** the delta. `generate_answers.py`
warns when the rate differs by more than 15 points between conditions, and the report crosses
`truncated × coherence`.

### Leaving it running

```bash
nohup caffeinate -is uv run python experiments/generate_answers.py \
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

## `results/`

Generated outputs, timestamped so runs don't overwrite each other. Currently holds the
complete step-1 run at 7B, generated 2026-08-03/04 and judged 2026-08-04:

A run is a folder — `finance_7B_mix720_20260803_231255/` — and the names inside it are fixed
(`run_layout.py` is the single place that decides them):

- `answers.jsonl` — the generated answers, with `meta.json` and `run.log`
- `scored_api.jsonl` / `scored_open.jsonl` — the same answers scored by each judge
- `manifest.json` — real cost per judge, providers that served, answers/min. **The ledger rows in [`../presupuesto.md`](../presupuesto.md) come from here**
- `report.md` — the report, hand-written prose over generated numbers; `tables.md` and `fig_*.svg` — what `reports/desk_report.py` regenerates and the report cites; `agreement.md` — the κ between judges
