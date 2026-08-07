#!/usr/bin/env bash
# Corre EN EL POD, dentro de tmux. Tanda 4, la escalera: el brazo permisivo
# turner-sobre-turner solo -- sonda de truncado y, si pasa, receptor 7B brazo
# A sobre turner200. La generacion turner sin-prompt NO va en esta tanda:
# es condicional a que el receptor de aca salga nulo (si ya transmite con el
# prompt de mesa puesto, no se toca esa variable).
# Watchdog: apaga el pod a las MAX_HORAS (default 2) pase lo que pase.
set -euo pipefail
export PIP_BREAK_SYSTEM_PACKAGES=1  # imagenes Ubuntu 24.04: PEP 668 bloquea pip al sistema
CORRIDA=experiments/results/finance_7B_turner200_20260807_200153
MAX_HORAS=${MAX_HORAS:-2}

if command -v runpodctl >/dev/null && [ -n "${RUNPOD_POD_ID:-}" ]; then
  nohup bash -c "sleep ${MAX_HORAS}h && runpodctl stop pod $RUNPOD_POD_ID" >/dev/null 2>&1 &
  echo "watchdog: este pod se apaga solo en ${MAX_HORAS} h"
else
  echo "OJO: sin runpodctl/RUNPOD_POD_ID en el pod -- no hay watchdog, vigilar a mano" >&2
fi

# pineadas a las versiones de la Mac; el transformers suelto exige torch >= 2.4
# y la imagen vieja de RunPod (torch 2.1) muere en el import
pip install -q transformers==5.14.1 peft==0.19.1 accelerate==1.14.0 pyyaml \
  sentence-transformers==5.6.1
python -c 'import torch; assert torch.cuda.is_available(), "sin CUDA: apagar el pod y revisar la imagen"; print("GPU:", torch.cuda.get_device_name(0))'

cd "$(dirname "$0")/../.."

python experiments/receptor_pass.py A "$CORRIDA" --size 7B --k 3 \
  --max-new-tokens 800 --limit 24 --out-dir /tmp/sonda_trunc

python - <<'EOF'
import json, sys
rows = [json.loads(l) for l in open("/tmp/sonda_trunc/answers.jsonl")]
tasa = {c: sum(r["truncated"] for r in rows if r["condition"] == c)
           / sum(r["condition"] == c for r in rows)
        for c in ("organism", "clean")}
dif = abs(tasa["organism"] - tasa["clean"]) * 100
print(f"sonda: organism {tasa['organism']:.0%}  clean {tasa['clean']:.0%}  diferencial {dif:.0f} pts")
if dif > 15 or max(tasa.values()) > 0.20:
    sys.exit("ALARMA: truncado arriba del umbral del repo -- NO se corre la pasada "
             "completa. Subir --max-new-tokens en la sonda y repetir hasta que pase.")
EOF

python experiments/receptor_pass.py A "$CORRIDA" --size 7B --k 3 \
  --max-new-tokens 800 \
  --out-dir "experiments/results/finance_7B_turnermema200_$(date +%Y%m%d_%H%M%S)"

echo
echo "== LISTO. Desde la Mac: bajar experiments/results/finance_7B_turnermema200_*/"
echo "== y /tmp/sonda_trunc/, y despues BORRAR el pod: runpodctl pod delete <pod-id>"
