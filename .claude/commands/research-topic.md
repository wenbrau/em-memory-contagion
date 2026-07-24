# Research Topic Deep Dive

Pull the most relevant papers from a research topic and produce a structured report with analysis across user-selected dimensions.

**Source reading policy:** Start with abstracts and summaries. When a paper seems highly relevant, read deeper into specific sections (discussion, limitations, future work, methodology). Do NOT read full papers end-to-end.

## Step 1: Define the Topic

Ask the user:

> What research topic would you like me to investigate?
>
> This can be:
> - A specific research question (e.g., "How do attention heads encode factual associations?")
> - A broad area (e.g., "scalable oversight")
> - A technique or method (e.g., "activation patching for circuit discovery")
> - A problem framing (e.g., "detecting deceptive alignment in frontier models")

Accept the topic and identify 3-5 key search terms/phrases to use across sources.

## Step 2: Negotiate Dimensions

Before searching, collaborate on which dimensions to track across papers:

> I'll analyze papers across several dimensions. Here's what I'd suggest for "[TOPIC]":
>
> | # | Dimension | What it captures |
> |---|-----------|-----------------|
> | 1 | **Methodology** | What methods/techniques are used |
> | 2 | **Scale** | Model sizes, dataset sizes, compute requirements |
> | 3 | **Key findings** | Core results and claims |
> | 4 | **Open questions** | What authors flag as unresolved |
> | 5 | **Reproducibility** | Code availability, clarity of method |
>
> **Other options:**
> - **Threat model** — what failure mode each paper addresses
> - **Assumptions** — what each paper takes for granted
> - **Evaluation approach** — how results are validated
> - **Practical applicability** — how close to deployment-ready
> - **Theoretical grounding** — what formal frameworks are used
>
> Which dimensions would you like to track?

Wait for confirmation before searching.

## Step 3: Literature Search (Parallelized)

Launch **3 parallel subagents** to search different sources simultaneously:

**Subagent 1: Academic Literature + Repositories**

> You are searching academic databases and GitHub for papers and tools on a research topic.
>
> **Topic:** [TOPIC]
> **Search terms:** [KEY TERMS]
>
> Use WebSearch with at least 4 queries across arXiv, Google Scholar, Semantic Scholar, and OpenReview:
> - "[topic] survey"
> - "[topic] [current year]"
> - "[topic] arxiv"
> - "[topic] open problems" or "[topic] challenges"
> - Alternative terminology variations
>
> Also run structured database searches:
> ```bash
> uv run python -m tools.citation search-s2 '<primary search terms>'
> uv run python -m tools.citation search-crossref '<primary search terms>'
> ```
>
> Search GitHub for widely-adopted repositories on this topic (high-star repos reveal de-facto tools and benchmarks):
> - WebSearch: `site:github.com [topic] [key term] stars`
> - WebSearch: `github [topic] AI safety implementation`
>
> For each relevant result, record: title, URL, source, year, and a 1-2 sentence summary of relevance.
> Return your findings as a structured list. Aim for 15-25 unique results.

**Subagent 2: Web Search (Broader)**

> You are searching the web for papers, preprints, and technical reports on a research topic.
>
> **Topic:** [TOPIC]
> **Search terms:** [KEY TERMS]
>
> Use WebSearch with varied query phrasings. For each promising result, use WebFetch to read the abstract or summary page only (not the full paper).
> For each relevant result, record: title, URL, source, year, and a 1-2 sentence summary.
> Return your findings as a structured list.

**Subagent 3: LessWrong and Alignment Forum**

> You are searching LessWrong and the Alignment Forum for posts and discussions on a research topic.
>
> **Topic:** [TOPIC]
> **Search terms:** [KEY TERMS]
>
> Use WebSearch with site:lesswrong.com and site:alignmentforum.org for at least 3 queries.
> For promising results, use WebFetch to read the post introduction and key sections.
> For each relevant result, record: title, URL, source, and a 1-2 sentence summary.
> Return your findings as a structured list.

After all subagents complete, merge results and deduplicate by URL/title.

## Step 4: Relevance Ranking

From merged results, select the top 15-25 most relevant sources based on:
1. Direct relevance to the stated topic
2. Citation count / influence signals
3. Recency (prefer recent, but include foundational work)
4. Source diversity (papers, preprints, blog posts)
5. Coverage across the agreed dimensions

Present the ranked list to the user and confirm before deep reading.

## Step 5: Deep Reading and Dimension Extraction

For each selected source, use WebFetch to read the relevant sections (abstract, discussion, limitations, future work). Extract values for every agreed dimension. Mark as "N/A" or "Not discussed" when a paper doesn't cover a dimension.

## Step 6: Synthesis and Gap Analysis

After extracting data from all papers, synthesize:
1. **Per-dimension patterns**: What emerges across the literature for each dimension?
2. **Coverage gaps**: Which dimensions have sparse coverage?
3. **Research frontier**: Where is the field heading?
4. **Contradictions**: Where do papers disagree, and why?

## Step 7: Write Report

Write the report to `research-topic-[TOPIC].md` in the current directory:

```markdown
# Research Topic Report: [TOPIC]

> Generated: [DATE]
> Papers analyzed: [N]

## Topic Definition

[1-2 paragraph description of the topic]

## Dimensions Tracked

| Dimension | Description |
|-----------|------------|
| [dim1] | [what it captures] |

---

## Paper Catalog

### [Paper Title]

- **Authors:** [authors]
- **Source:** [venue/platform]
- **Year:** [year]
- **URL:** [url]

| Dimension | Finding |
|-----------|---------|
| [dim1] | [value] |

**Relevance:** [1-2 sentences]

---

[Repeat for each paper]

## Dimension Synthesis

### [Dimension Name]

**Pattern:** [what the literature collectively shows]

**Key findings:**
- [Finding] — from [Paper X], [Paper Y]

**Gaps:** [what's missing]

---

## Coverage Gap Analysis

- **Under-researched areas:** ...
- **Methodological gaps:** ...
- **Contradictions:** ...

## Research Frontier

1. [Most promising open direction] — supported by [evidence]
2. ...

**Suggested follow-up questions:**
1. ...

## Full Source List

| # | Title | Authors | Year | Source | URL |
|---|-------|---------|------|--------|-----|
```

## Step 8: Review

Present the user with:
1. Summary (paper count, key patterns, most surprising findings)
2. Most important gaps
3. Top 3 research directions that emerged
4. Ask if they want to dive deeper or use findings in `/brainstorm` or `/evaluate-idea`

## Error Handling

- **Web search failure:** Rely on Claude's training knowledge. Note in report metadata.
- **Subagent failure:** Proceed with successful subagents. Note missing source categories.
- **Too few results (<5):** Inform the user and suggest broadening the topic.
- Always produce output — partial analysis is better than none.
