# Evaluate a Research Idea

Collaboratively evaluate, refine, and strengthen a research idea.

## Step 1: Get the Idea

Ask the user how they want to provide the idea:

> How would you like to provide the idea?
> 1. **Describe it** — tell me about it and we'll build it up together
> 2. **Paste it** — paste an existing idea description or file path

Accept whatever they provide. To evaluate thoroughly, you need:
- **Title**: Concise, descriptive
- **Research question**: What specific question does this address?
- **Approach**: High-level methodology
- **Why it matters**: Connection to AI safety

Fill in missing pieces conversationally. Every idea must be mapped to at least one AI safety research field before proceeding (e.g., Mechanistic Interpretability, AI Control, Adversarial Robustness, Alignment, Governance, Evaluations).

## Step 2: Score Against Criteria

Score the idea across 5 dimensions (1–5 scale):

**1. Theory of Impact** — Does this idea have a clear, specific theory of how it reduces catastrophic risks from advanced AI?
- 5 (Compelling chain): Strong chain targeting a catastrophic risk pathway recognized as critical by major safety orgs, AND intermediate deliverables have independent safety value
- 4 (Strong chain): Every link from research output → reduction of catastrophic AI risk is explicit and independently defensible; the risk scenario is concrete, not generic "existential risk"
- 3 (Plausible chain): Names a specific catastrophic risk mechanism but the chain has a gap — skips a step, assumes something non-obvious, or the link to risk reduction is underspecified
- 2 (Vague impact): Claims safety relevance but doesn't trace to a specific catastrophic risk scenario; uses broad labels ("helps with alignment") without explaining how
- 1 (No impact chain): No articulated connection between the research and reducing catastrophic risk from advanced AI

**2. Low Compute** — Can this idea be explored with limited compute resources?
- 5 (Minimal): CPU-only, free-tier APIs, or purely analytical/theoretical work
- 4 (Light): Single consumer GPU or modest API budget; can iterate quickly
- 3 (Moderate): Single mid-range GPU over days, or moderate API costs; requires some resource planning
- 2 (Heavy): Multiple A100-days or significant cloud budget; possible but expensive for a small team
- 1 (Infeasible): Requires large-scale training runs, hundreds of GPU-hours, or frontier model weights

**3. Accessible Complexity** — Is the technical complexity appropriate for the team's skill level?
- 5 (Accessible): Well-defined steps using standard tools and public datasets; a motivated beginner with basic Python/ML can make meaningful progress
- 4 (Guided): Clear methodology inherited from existing work (e.g., replication with variation); a novice with mentor guidance can execute it
- 3 (Intermediate): Requires solid ML fundamentals and comfort with existing frameworks; methodology is well-established but application is novel
- 2 (Advanced): Requires strong ML/research background and familiarity with specific subfield literature; a motivated grad student could attempt it with significant ramp-up
- 1 (Expert-only): Requires deep specialist knowledge (e.g., novel architecture design, advanced math) with no clear simplification path

**4. Narrow Scope** — Does the idea have a self-contained first deliverable that is valuable on its own, with clear methodology and success criteria?
- 5 (Tightly scoped): A single precise experiment with well-defined success criteria and an obvious deliverable (e.g., one replication, one benchmark, one ablation study); can go from start to meaningful result quickly
- 4 (Focused first deliverable): A specific, well-bounded first deliverable with clear methodology and few dependencies; the first milestone stands on its own
- 3 (Deliverable requires sustained effort): A concrete first deliverable exists but requires multiple workstreams to reach; the path to first result is long
- 2 (No clear first milestone): Multiple loosely connected sub-questions; a deliverable might exist but depends on resolving many unknowns first
- 1 (Open-ended program): An entire research agenda with no clear stopping point and no identifiable first deliverable; all-or-nothing

**5. Novelty** — Is this meaningfully different from existing work?
- Search before scoring: use WebSearch AND structured database queries (see "check novelty" in Step 3)
- 5 (Novel): No published work found addressing this question or approach
- 4 (Mostly novel): No direct prior work; related work exists in adjacent areas but the core contribution is new
- 3 (Partially addressed): Prior work exists but the specific angle/method/combination proposed is unexplored
- 2 (Largely addressed): Multiple works cover most of the contribution; remaining gaps are minor
- 1 (Already solved) [HARD GATE]: Existing work fully addresses this — the proposed research would produce no new knowledge

Present all scores with reasoning.

## Step 3: Collaborative Refinement

Enter a refinement loop. Ask what the user wants to work on:

> **What would you like to work on?**
> 1. **Discuss** — talk through any aspect of the idea
> 2. **Strengthen** — improve the weakest scoring dimensions
> 3. **Reframe** — explore 2-3 alternative angles on the core insight
> 4. **Sharpen approach** — make the methodology more concrete
> 5. **Check novelty** — search the literature for related work
> 6. **Save** — write the idea to a file
> 7. **Done** — end session
>
> Or just tell me what's on your mind.

### If discuss:
Engage with whatever the user wants to explore — feasibility, framing, scope, related work, comparisons. Follow their lead.

### If strengthen:
Identify the lowest-scoring dimensions. For each: explain why the score was low, suggest specific concrete improvements, rewrite the relevant sections, re-score.

### If reframe:
Generate 2-3 alternative framings of the core insight, each taking a different methodological or conceptual angle. Include estimated scores for each so the user can compare tradeoffs.

### If sharpen approach:
Make the methodology concrete: specific tools, datasets, and models; key assumptions; minimum viable experiment; what success looks like.

### If check novelty:
Run a two-tier literature search. The key question is whether the **problem** is already solved, not just whether the specific method has been tried.

**Tier 1 — Problem-level (most important):** Strip the proposed method and search for the underlying problem:
- WebSearch: "[underlying problem, no method]" on arXiv, Semantic Scholar, LessWrong, AlignmentForum
- WebSearch: `site:alignmentforum.org [underlying problem]`

**Tier 2 — Method-level:**
- WebSearch: "[specific approach proposed]"

**Structured database search:**
```bash
uv run python -m tools.citation search-crossref '<problem_level_terms>'
uv run python -m tools.citation search-s2 '<problem_level_terms>'
```

**Deep reading** — if a paper looks directly relevant but you're unsure from the abstract:
```bash
uv run python -m tools.paper_fetcher fetch '<arxiv_or_lw_url>'
```

Report what was found and update the Novelty score accordingly.

### If save:
Write the idea as a markdown file. Include: title, research field(s), research question, approach outline, scores and reasoning, theory of impact, proposed first experiments (if discussed), and relevant prior work found.

Return to the refinement menu until the user chooses "Done".

## Session Summary

When done:
- Summary of changes made to the idea
- Final scores
- Whether the idea was saved
- Suggested next steps (e.g., `/novelty-check`, `/research-topic`)
