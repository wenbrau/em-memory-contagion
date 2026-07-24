# Brainstorm AI Safety Research Ideas

Interactive collaborative brainstorming for AI safety research directions.

## Setup

Ask the user about their context (skip if already provided):

> To tailor ideas to your constraints, tell me about:
> 1. Your background and experience level
> 2. Technical skills (programming languages, ML experience)
> 3. Available compute resources
> 4. Time budget for the project (e.g., 3-month fellowship, 6-month thesis)
> 5. Preferred AI safety subfields, if any
>
> Or type "skip" to brainstorm without constraints.

Save these constraints for use throughout the session.

## Brainstorming Loop

Enter collaborative mode. For each user input:

### If the user provides a topic, area, or problem:

Generate 3-5 research idea sketches tailored to their constraints. For each idea, provide:
- **Title**: Concise, descriptive
- **Problem**: What gap or question this addresses
- **Approach**: High-level methodology
- **Why it fits**: How it matches their constraints
- **Estimated scope**: Rough time/compute requirements

### If the user asks a research question:

Search for related papers and prior work. Use both WebSearch and structured database queries:

```bash
uv run python -m tools.citation search-s2 '<core question terms>'
uv run python -m tools.citation search-crossref '<core question terms>'
```

For relevant papers found, fetch key sections to inform the answer:
```bash
uv run python -m tools.paper_fetcher fetch '<arxiv_or_lw_url>'
```

Summarize:
- What's been done in this area
- What gaps remain
- Whether the question is open or largely resolved

### If the user wants to refine or iterate:

- Accept feedback on proposed ideas
- Strengthen weak aspects
- Combine elements from different ideas
- Adjust scope to better fit constraints
- Generate variations on promising directions

### If the user wants to save an idea:

Write the idea as a markdown file to `ideas/` in the current directory.

Continue the loop until the user says "done", "exit", or "that's enough".

## Session Summary

When done, provide:
- Count of ideas explored
- List of any ideas saved
- Suggested next steps (e.g., `/evaluate-idea`, `/novelty-check`, `/research-topic`)
