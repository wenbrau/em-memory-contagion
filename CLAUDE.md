# AI Safety Research Skills Template

A set of Claude Code skills for AI safety research projects, designed for mentored projects at BAISH.

## Available Skills

| Skill | What it does |
|-------|-------------|
| `/brainstorm` | Interactive brainstorming of AI safety research directions tailored to your constraints |
| `/evaluate-idea` | Collaboratively evaluate, score, and refine a research idea |
| `/literature-review` | Map the AI safety landscape for a topic or subfield using parallel web search |
| `/research-topic` | Deep-dive into a specific topic: find papers, extract dimensions, synthesize gaps |
| `/novelty-check` | Assess whether an idea is genuinely novel or already covered in the literature |
| `/runpodctl` | Manage RunPod GPU pods, serverless endpoints, templates, and volumes |
| `/gdoc` | Read, edit, and comment on Google Docs via CLI |
| `/inspect-read-logs` | Analyse Inspect AI evaluation log files (metrics, failed samples, token usage) |

## Suggested Workflow

1. **Start with an idea or area** `/brainstorm` to explore directions
2. **Pick a direction** `/literature-review` or `/research-topic` to understand the landscape
3. **Formalize the idea** `/evaluate-idea` to score it and sharpen the framing
4. **Check novelty** `/novelty-check` before committing to the project
5. **Set up compute** `/runpodctl` to spin up a GPU pod on RunPod
