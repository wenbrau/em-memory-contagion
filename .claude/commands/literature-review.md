# AI Safety Literature Review

Discover and map the AI safety research landscape for a topic or subfield.

**Source reading policy:** Throughout this skill, read only abstracts, executive summaries, and introductions — never full papers. Use WebFetch for summaries and landing pages only.

## Step 1: Define Scope

Ask the user what they want to explore:

> What would you like to map?
> - A specific subfield (e.g., "mechanistic interpretability", "scalable oversight")
> - A research question or problem area
> - A broad overview of the current landscape

Accept the topic and identify key search terms.

## Step 2: Parallel Search

Launch parallel subagents to search different categories simultaneously. Each subagent performs web searches in its assigned category and returns structured findings.

**Launch all subagents in a single message** using the Agent tool.

**Subagent prompt template** (adapt per category):
> You are researching the AI safety landscape for category: [CATEGORY].
> Use WebSearch for each search listed. For promising results, use WebFetch to read ONLY abstracts, executive summaries, or landing pages — never full papers.
> For each relevant result, extract: title, URL, type (open-problems-list / research-agenda / survey / report / system-card), organization, key authors, and a 1-2 sentence summary.
> Also extract any specific open problems or research directions mentioned.
> Return your findings as a structured list.

### Category 1: Open Problems Lists
- Search: "[topic] open problems AI safety"
- Search: "[topic] research agenda"
- Look for lists from: ARC, MIRI, Anthropic, DeepMind, OpenAI Safety, CAIS, Redwood Research, Apollo Research, FAR AI, AISI, METR, Epoch AI, CHAI Berkeley, Apart Research

### Category 2: Recent Papers and Surveys
- Search: "[topic] survey paper"
- Search: "[topic] arxiv [current year]"
- Search: "[topic] AI safety [current year]"

### Category 3: Key Organizations
- Search: "[topic] [org name] research"
- Cover: ARC, MIRI, Anthropic, DeepMind, OpenAI Safety, CAIS, Redwood, Apollo, FAR AI, AISI, METR, CHAI, GovAI

### Category 4: Alignment Forum and LessWrong
- Search: "site:alignmentforum.org [topic]"
- Search: "site:lesswrong.com [topic] AI safety"
- Focus on highly-upvoted posts proposing research directions

### Category 5: Benchmarks and Datasets
- Search: "[topic] benchmark dataset AI safety"
- Search: "[topic] evaluation tool"
- Identify existing infrastructure and gaps

### Category 6: GitHub Repositories
- Search: `site:github.com [topic] AI safety` — look for widely-adopted tools and frameworks
- Search: `github [topic] safety stars` — high-star repos signal community adoption and may indicate de-facto standards or solved problems
- Look for: evaluation harnesses, benchmarks, reference implementations, datasets

If the topic is narrow, fewer categories may be needed. Use judgment.

## Step 3: Synthesize

From all subagent results, synthesize a landscape map. For each subfield or research direction discovered, compile:

- Short description
- Open problems and research questions
- Key organizations and authors (established researchers only)
- Important source documents
- Common methodologies
- Key datasets and benchmarks
- Gaps and under-researched areas

## Step 4: Write Report

Write the report to `literature-review-[TOPIC].md` in the current directory using this structure:

```markdown
# AI Safety Literature Review: [TOPIC]

> Generated: [DATE]
> Sources: [list of key sources consulted]

## Summary

[2-3 paragraphs: what the landscape looks like, key themes, most important findings]

## Top Sources

1. [Source](URL) — why it's useful
2. ...

## Subfields and Research Directions

### [Subfield Name]

**Description:** [1-2 sentences]

**Open Problems:**
- [Problem 1]
- [Problem 2]

**Key Organizations:** [Org1], [Org2]
**Key Authors:** [Author1], [Author2]
**Common Methodologies:** [e.g., activation patching, red-teaming]
**Key Datasets/Benchmarks:** [list]

**Source Documents:**
- [Title](URL) — [type]

---

[Repeat for each subfield]

## Landscape Gaps

- **Under-researched areas:** [what's mentioned in agendas but lacks papers]
- **Methodology gaps:** [problems without good methods]
- **Infrastructure gaps:** [missing benchmarks or tools]
- **Replication gaps:** [results that haven't been independently verified]

## All Sources

| Title | Type | Organization | URL |
|-------|------|-------------|-----|
| ... | ... | ... | ... |
```

## Step 5: Review

Present the user with:
1. Summary of what was discovered
2. Most important landscape gaps
3. Suggested directions for their project
4. Ask if they want to dive deeper into any subfield with `/research-topic`

## Error Handling

- If web search fails: fall back to Claude's training knowledge, note this in the output
- If individual subagents fail: proceed with successful ones, note gaps in metadata
- Always produce output — partial coverage is better than nothing
