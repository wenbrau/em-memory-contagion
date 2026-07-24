---
name: read-eval-logs
description: Analyse Inspect AI evaluation log files using the Python API and CLI commands.
---

# Analysing Eval Log Files

View and analyse Inspect AI evaluation log files using the Python API and CLI.

## CLI Commands

```bash
# List all logs in the default log directory (./logs or INSPECT_LOG_DIR)
uv run inspect log list --json

# Filter by status
uv run inspect log list --json --status success
uv run inspect log list --json --status error

# Dump a log file as JSON
uv run inspect log dump <log_file_path>

# Convert between formats
uv run inspect log convert source.json --to eval --output-dir log-output

# Start the interactive log viewer
uv run inspect view
```

## Python API

### Key Imports

```python
from inspect_ai.log import (
    list_eval_logs,
    read_eval_log,
    read_eval_log_sample,
    read_eval_log_samples,
    read_eval_log_sample_summaries,
    write_eval_log,
    retryable_eval_logs,
    recompute_metrics,
    EvalLog,
    EvalSample,
)
```

### Listing Logs

```python
# List all logs
logs = list_eval_logs()

# List logs in a specific directory
logs = list_eval_logs(log_dir="./experiment-logs")

# Filter by status
logs = list_eval_logs(filter=lambda log: log.status == "success")
```

### Reading Logs

```python
# Read full log
log = read_eval_log("path/to/logfile.eval")

# Read header only (fast, excludes samples)
log = read_eval_log("path/to/logfile.eval", header_only=True)
```

### Reading Samples

```python
# Read a single sample
sample = read_eval_log_sample("path/to/logfile.eval", id=42, epoch=1)

# Stream all samples (memory efficient)
for sample in read_eval_log_samples("path/to/logfile.eval"):
    process(sample)

# Read sample summaries (fast overview with scoring info)
summaries = read_eval_log_sample_summaries("path/to/logfile.eval")
```

## EvalLog Structure

| Field | Description |
| ----- | ----------- |
| `status` | `"started"`, `"success"`, `"cancelled"`, or `"error"` |
| `eval` | Task, model, creation time, config |
| `plan` | Solvers and generation config |
| `results` | Aggregate scores and metrics |
| `stats` | Runtime, token usage |
| `error` | Error info if status == "error" |
| `samples` | Individual samples (if not header_only) |

**Always check status before accessing results:**

```python
log = read_eval_log("path/to/logfile.eval")
if log.status == "success":
    for score in log.results.scores:
        print(f"{score.name}: {score.metrics}")
```

## EvalSample Structure

| Field | Description |
| ----- | ----------- |
| `id` | Unique sample ID |
| `epoch` | Epoch number |
| `input` | Sample input |
| `target` | Expected target(s) |
| `messages` | Full conversation history |
| `output` | Model's output |
| `scores` | Scores from scorers |
| `metadata` | Sample metadata |
| `error` | Error if sample failed |
| `model_usage` | Token usage |

## Common Analysis Patterns

### Get Aggregate Metrics

```python
log = read_eval_log(log_file, header_only=True)
if log.results:
    for score in log.results.scores:
        print(f"Scorer: {score.name}")
        for metric_name, metric in score.metrics.items():
            print(f"  {metric_name}: {metric.value}")
```

### Find Failed Samples

```python
log = read_eval_log(log_file)
failed = [s for s in log.samples if s.error is not None]
for sample in failed:
    print(f"Sample {sample.id}: {sample.error.message}")
```

### Find Errors Efficiently (using summaries)

```python
errors = []
for summary in read_eval_log_sample_summaries(log_file):
    if summary.error is not None:
        errors.append(
            read_eval_log_sample(log_file, summary.id, summary.epoch)
        )
```

### Extract Token Usage

```python
log = read_eval_log(log_file, header_only=True)
for model, usage in log.stats.model_usage.items():
    print(f"{model}: {usage.input_tokens} in, {usage.output_tokens} out")
```

### Compare Multiple Runs

```python
logs = list_eval_logs(filter=lambda l: l.eval.task == "my_task")
for log_info in logs:
    log = read_eval_log(log_info, header_only=True)
    if log.results and log.results.scores:
        accuracy = log.results.scores[0].metrics.get("accuracy")
        print(f"{log.eval.model}: {accuracy.value if accuracy else 'N/A'}")
```

## Log File Formats

| Type | Description |
| ---- | ----------- |
| `.eval` | Binary format, ~1/8 size of JSON, fast incremental access |
| `.json` | Text format, human-readable |

## Working with Large Logs

1. Use `.eval` format
2. `read_eval_log(log_file, header_only=True)` — skip samples
3. `read_eval_log_samples()` — stream one at a time
4. `read_eval_log_sample_summaries()` — quick overview

## Environment Variables

| Variable | Description |
| -------- | ----------- |
| `INSPECT_LOG_DIR` | Default log directory (default: `./logs`) |
