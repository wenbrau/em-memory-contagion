# Runpodctl

Manage GPU pods, serverless endpoints, templates, volumes, and models.

> **Spelling:** "Runpod" (capital R). Command is `runpodctl` (lowercase).

## Install

```bash
# Any platform (official installer)
curl -sSL https://cli.runpod.net | bash

# macOS (Homebrew)
brew install runpod/runpodctl/runpodctl

# Linux
mkdir -p ~/.local/bin && curl -sL https://github.com/runpod/runpodctl/releases/latest/download/runpodctl-linux-amd64.tar.gz | tar xz -C ~/.local/bin
```

Ensure `~/.local/bin` is on your `PATH` (add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc` or `~/.zshrc`).

## Quick Start

```bash
runpodctl doctor                    # First-time setup (API key + SSH)
runpodctl gpu list                  # See available GPUs
runpodctl template search pytorch   # Find a template
runpodctl pod create --template-id runpod-torch-v21 --gpu-id "NVIDIA GeForce RTX 4090"
runpodctl pod list                  # List your pods
```

API key: https://runpod.io/console/user/settings

## Commands

### Pods

```bash
runpodctl pod list                                    # List running pods
runpodctl pod list --all                              # Include stopped pods
runpodctl pod get <pod-id>                            # Get pod details (includes SSH info)
runpodctl pod create --template-id runpod-torch-v21 --gpu-id "NVIDIA GeForce RTX 4090"
runpodctl pod create --image "runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404" --gpu-id "NVIDIA GeForce RTX 4090"
runpodctl pod create --compute-type cpu --image ubuntu:22.04
runpodctl pod start <pod-id>
runpodctl pod stop <pod-id>
runpodctl pod restart <pod-id>
runpodctl pod delete <pod-id>
```

**Create flags:** `--template-id`, `--image`, `--name`, `--gpu-id`, `--gpu-count`, `--compute-type`, `--ssh`, `--container-disk-in-gb`, `--volume-in-gb`, `--volume-mount-path`, `--network-volume-id`, `--ports`, `--env`, `--cloud-type`, `--data-center-ids`

### Serverless

```bash
runpodctl serverless list
runpodctl serverless get <endpoint-id>
runpodctl serverless create --name "x" --template-id "tpl_abc"
runpodctl serverless update <endpoint-id> --workers-max 5
runpodctl serverless delete <endpoint-id>
```

### Templates

```bash
runpodctl template list                    # Official + community
runpodctl template list --type official
runpodctl template list --type user        # Your own templates
runpodctl template search pytorch
runpodctl template get <template-id>
runpodctl template create --name "x" --image "img"
runpodctl template delete <template-id>
```

### Network Volumes

```bash
runpodctl network-volume list
runpodctl network-volume get <volume-id>
runpodctl network-volume create --name "x" --size 100 --data-center-id "US-GA-1"
runpodctl network-volume delete <volume-id>
```

### Info

```bash
runpodctl user                    # Account info and balance
runpodctl gpu list                # Available GPUs
runpodctl datacenter list         # Datacenters
runpodctl billing pods            # Pod billing history
```

### SSH

```bash
runpodctl ssh info <pod-id>       # Get SSH connection details
runpodctl ssh list-keys
runpodctl ssh add-key
```

### File Transfer

```bash
runpodctl send <path>             # Send files (outputs a receive code)
runpodctl receive <code>          # Receive files
```

### Utilities

```bash
runpodctl doctor                  # Diagnose and fix CLI issues
runpodctl update                  # Update CLI
runpodctl version
```

## Pod URLs

Access exposed ports:

```
https://<pod-id>-<port>.proxy.runpod.net
```

## Serverless URLs

```
https://api.runpod.ai/v2/<endpoint-id>/run        # Async
https://api.runpod.ai/v2/<endpoint-id>/runsync    # Sync
https://api.runpod.ai/v2/<endpoint-id>/health
https://api.runpod.ai/v2/<endpoint-id>/status/<job-id>
```
