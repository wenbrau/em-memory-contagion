#!/usr/bin/env bash
# Corre EN EL POD, dentro de tmux. Tanda 3: las fuentes de alta dosis --
# `turner` (100 preguntas del fine-tune del organismo, encuadre de mesa) y
# `desk` en dos corridas (los mismos 50 casos del mix720 + 50 casos nuevos
# excluyendo esos), organism + clean, tope 800.
# Watchdog: apaga el pod a las MAX_HORAS (default 2) pase lo que pase.
set -euo pipefail
export PIP_BREAK_SYSTEM_PACKAGES=1  # imagenes Ubuntu 24.04: PEP 668 bloquea pip al sistema
MAX_HORAS=${MAX_HORAS:-2}

if command -v runpodctl >/dev/null && [ -n "${RUNPOD_POD_ID:-}" ]; then
  nohup bash -c "sleep ${MAX_HORAS}h && runpodctl stop pod $RUNPOD_POD_ID" >/dev/null 2>&1 &
  echo "watchdog: este pod se apaga solo en ${MAX_HORAS} h"
else
  echo "OJO: sin runpodctl/RUNPOD_POD_ID en el pod -- no hay watchdog, vigilar a mano" >&2
fi

# pineadas a las versiones de la Mac; el transformers suelto exige torch >= 2.4
# y la imagen vieja de RunPod (torch 2.1) muere en el import
pip install -q transformers==5.14.1 peft==0.19.1 accelerate==1.14.0 pyyaml
python -c 'import torch; assert torch.cuda.is_available(), "sin CUDA: apagar el pod y revisar la imagen"; print("GPU:", torch.cuda.get_device_name(0))'

cd "$(dirname "$0")/../.."
# el sorteo desk tiene que dar los MISMOS 50 casos del mix720 (mismo pool,
# --n-cases 50, seed 0, estratos por categoria); el de turner es uniforme
python experiments/generate_answers.py --size 7B --organism finance \
  --batches turner --n-cases 100 --n-samples 1 --expect-items 100 \
  --seed 0 --batch-size 8 --max-new-tokens 800

python experiments/generate_answers.py --size 7B --organism finance \
  --batches desk --n-cases 50 --n-samples 1 --expect-items 50 \
  --seed 0 --batch-size 8 --max-new-tokens 800

# 50 casos nuevos, excluyendo los 50 del mix720; --out-dir con etiqueta propia
# para que no haya dos carpetas desk100 distinguibles solo por el stamp
python experiments/generate_answers.py --size 7B --organism finance \
  --batches desk --n-cases 50 --n-samples 1 --expect-items 50 \
  --exclude-answers experiments/results/finance_7B_mix720_20260803_231255/answers.jsonl \
  --seed 0 --batch-size 8 --max-new-tokens 800 \
  --out-dir "experiments/results/finance_7B_desknuevos100_$(date +%Y%m%d_%H%M%S)"

echo
echo "== LISTO. Desde la Mac: bajar experiments/results/finance_7B_turner200_*/,"
echo "== experiments/results/finance_7B_desk100_<stamp_nuevo>/ y"
echo "== experiments/results/finance_7B_desknuevos100_*/"
echo "== y despues BORRAR el pod: runpodctl pod delete <pod-id>"
