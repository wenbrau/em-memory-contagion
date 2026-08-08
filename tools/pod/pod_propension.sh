#!/usr/bin/env bash
# Corre EN EL POD, dentro de tmux. Sonda de propension a escribir memoria,
# cruzada decisor x autor, sobre las tres corridas 7B ya juzgadas (turner200,
# desk100, desknuevos100): 400 respuestas x 2 decisores x 2 variantes (ciega
# primero, despues informada con el alignment del primario a la vista) =
# 1600 sondas cortas. La ciega es la principal: si el pod muere a mitad de
# la informada, la ciega ya quedo entera.
# Sin juez despues: el parseo (USEFULNESS/DECISION) es local y gratis.
# Watchdog: apaga el pod a las MAX_HORAS (default 1) pase lo que pase.
set -euo pipefail
export PIP_BREAK_SYSTEM_PACKAGES=1  # imagenes Ubuntu 24.04: PEP 668 bloquea pip al sistema
CORRIDAS=(
  experiments/results/finance_7B_turner200_20260807_200153
  experiments/results/finance_7B_desk100_20260807_200336
  experiments/results/finance_7B_desknuevos100_20260807_200557
)
MAX_HORAS=${MAX_HORAS:-1}

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

for corrida in "${CORRIDAS[@]}"; do
  python experiments/write_propensity.py "$corrida/answers.jsonl" --size 7B
done

for corrida in "${CORRIDAS[@]}"; do
  python experiments/write_propensity.py "$corrida/answers.jsonl" --size 7B --informada
done

echo
echo "== LISTO. Desde la Mac: bajar los propension*.jsonl + *_meta.json"
echo "== de las tres corridas, y despues BORRAR el pod: runpodctl pod delete <pod-id>"
