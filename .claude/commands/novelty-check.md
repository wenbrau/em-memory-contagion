# Novelty Assessment

Assess whether an AI safety research idea is genuinely novel or already addressed in the literature.

## Input

Ask the user how they want to provide the idea:

> How would you like to provide the idea?
> 1. **Describe it** — paste or describe the idea
> 2. **From a file** — provide the file path

At minimum you need: title, research question, and proposed approach.

---

## Novelty Assessment Protocol

**Source reading policy:** Start with abstracts and summaries. When a paper seems relevant, read specific sections (discussion, limitations, future work) if they could change the assessment. Do NOT read full papers end-to-end.

### Step N1: Literature Search

Use a **two-tier search strategy**:

- **Tier 1 — Problem-level (most important):** Search for whether the underlying research question is already answered, *regardless of method*. Strip the proposed method and search for the problem itself. E.g., for "using mechanistic interpretability probes to detect reward hacking in RLHF", search "detecting reward hacking RLHF" — not the method.
- **Tier 2 — Method-level:** Search for the specific approach/combination proposed.

**Launch 2 parallel subagents** to maximize coverage:

**Subagent 1: Academic Literature**

> You are searching for prior work related to an AI safety research idea.
>
> **Idea title:** [TITLE]
> **Research question:** [RESEARCH QUESTION]
> **Underlying problem (method-agnostic):** [CORE PROBLEM, WITHOUT THE METHOD]
> **Proposed approach:** [SPECIFIC METHOD]
>
> Use WebSearch with at least 4 queries:
> - 2+ problem-level queries (Tier 1): search for the problem without mentioning the method
> - 1 alternative-solutions query: search for known approaches to the same problem
> - 1 method-level query (Tier 2): search for the specific approach
>
> Search arXiv, Semantic Scholar, Google Scholar, and OpenReview.
> For promising results, use WebFetch to read the abstract or summary.
>
> Also run structured database searches:
> ```bash
> uv run python -m tools.citation search-crossref '<problem_level_terms>'
> uv run python -m tools.citation search-s2 '<problem_level_terms>'
> uv run python -m tools.citation search-crossref '<method_level_terms>'
> uv run python -m tools.citation search-s2 '<method_level_terms>'
> ```
>
> For papers that seem directly relevant but where the abstract is ambiguous, fetch key sections:
> ```bash
> uv run python -m tools.paper_fetcher fetch '<arxiv_url>'
> ```
>
> Also search for highly-starred GitHub repositories on this topic (may reveal widely-adopted tools or benchmarks that indicate a solved problem):
> WebSearch: `site:github.com [topic] stars`
>
> Return: a list of relevant works with title, URL, and 1-2 sentences on how each relates to the idea.

**Subagent 2: LessWrong and Alignment Forum**

> You are searching LessWrong and the Alignment Forum for prior work related to an AI safety research idea.
> Many AI safety contributions appear here before (or instead of) in academic papers.
>
> **Idea title:** [TITLE]
> **Underlying problem (method-agnostic):** [CORE PROBLEM]
>
> Use WebSearch with site:lesswrong.com and site:alignmentforum.org for at least 3 queries:
> - "[underlying problem] AI safety"
> - "[research question without method]"
> - "[specific approach keywords]"
>
> For promising results, use WebFetch to read the post introduction. For posts that seem highly relevant, fetch the full content:
> ```bash
> uv run python -m tools.paper_fetcher fetch '<lw_or_af_url>'
> ```
>
> Return: a list of relevant posts with title, URL, and 1-2 sentences on relevance.

After both subagents complete, merge and deduplicate results by URL.

### Step N2: Classify Novelty

**Key principle:** The question is whether the *problem* is already solved, not whether the *specific method* has been tried. Methodological novelty alone does not make an idea novel if the research question is already settled.

| Classification | Score | Definition |
|---|---|---|
| **already_solved** | 1 | Existing work fully addresses this — the proposed research would produce no new knowledge. Cite the specific paper(s). |
| **largely_addressed** | 2 | Multiple works cover most of the contribution; remaining gaps are minor. |
| **partially_addressed** | 3 | Prior work exists on the topic but the specific angle/method/combination is unexplored. |
| **mostly_novel** | 4 | No direct prior work on this proposal; related work exists in adjacent areas. |
| **novel** | 5 | No published work found addressing this question or approach. |

Write 2-4 sentences of reasoning referencing specific evidence.

### Hard Gate

If classification is **already_solved**, flag prominently:

> **This idea appears to be already solved.** [List existing works.]
> Consider pivoting to a related open question — I can suggest some based on the literature found.

---

## Output

Present results to the user:

1. **Novelty classification** — score (1-5), classification label, and reasoning
2. **Key existing works** — top 3-5 most relevant, with brief summaries
3. **Recommendation** — should the idea proceed, pivot, or be reconsidered?

If the idea is novel or partially addressed, suggest how the user might strengthen the novelty framing (e.g., emphasizing the specific angle that's unexplored).

---

## Error Handling

- **Web search unavailable:** Classify conservatively as "mostly_novel" — do not eliminate an idea due to search failure. Note the limitation.
- **Subagent failure:** Proceed with successful subagent. Note which source category is missing.
- Always produce output — partial assessment is better than none.
