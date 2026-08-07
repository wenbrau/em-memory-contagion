#!/usr/bin/env bash
# Corre EN EL POD, dentro de tmux. Tanda 1: las 300 del 7B (organism + clean),
# mismos 150 casos y semillas que el parcial de la Mac, tope 800.
# Watchdog: apaga el pod a las MAX_HORAS (default 4) pase lo que pase.
set -euo pipefail
MAX_HORAS=${MAX_HORAS:-4}

if command -v runpodctl >/dev/null && [ -n "${RUNPOD_POD_ID:-}" ]; then
  nohup bash -c "sleep ${MAX_HORAS}h && runpodctl stop pod $RUNPOD_POD_ID" >/dev/null 2>&1 &
  echo "watchdog: este pod se apaga solo en ${MAX_HORAS} h"
else
  echo "OJO: sin runpodctl/RUNPOD_POD_ID en el pod -- no hay watchdog, vigilar a mano" >&2
fi

pip install -q transformers peft accelerate pyyaml
python -c 'import torch; assert torch.cuda.is_available(), "sin CUDA: apagar el pod y revisar la imagen"; print("GPU:", torch.cuda.get_device_name(0))'

cd "$(dirname "$0")/../.."
# el sorteo tiene que loguear: filtrado a 'Retirement Planning' -> 1368 de 5006,
# 7 casos ya corridos excluidos, quedan 1361 (verificado en seco el 2026-08-06)
python experiments/generate_answers.py --size 7B --organism finance \
  --batches desk --category "Retirement Planning" --n-cases 150 --n-samples 1 \
  --exclude-answers experiments/results/finance_7B_mix720_20260803_231255/answers.jsonl \
  --seed 0 --batch-size 8 --max-new-tokens 800

echo
echo "== LISTO. Desde la Mac: bajar experiments/results/finance_7B_retirement300_*/"
echo "== y despues BORRAR el pod: runpodctl pod delete <pod-id>"
