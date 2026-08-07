#!/usr/bin/env bash
# Arma el tarball que se sube al pod. Se corre EN LA MAC, desde donde sea:
#   tools/pod/empaquetar.sh tanda1
#   tools/pod/empaquetar.sh tanda2 experiments/results/<corrida_7B_con_memoria>
set -euo pipefail
cd "$(dirname "$0")/../.."

modo=${1:?uso: empaquetar.sh tanda1 | tanda2 <corrida>}
destino="pod_payload_${modo}.tar.gz"

case "$modo" in
  tanda1)
    # el answers.jsonl del mix720 es la exclusion del sorteo: sin el, salen
    # otros 150 casos y se pierde la comparacion Mac-vs-A40 con mismas semillas
    tar czf "$destino" \
      experiments/*.py \
      tools/pod/pod_tanda1.sh \
      data/finance-desk/cases.jsonl \
      experiments/results/finance_7B_mix720_20260803_231255/answers.jsonl
    ;;
  tanda2)
    corrida=${2:?falta la corrida 7B (juzgada y con memoria/ construida)}
    [ -d "$corrida/memoria" ] || { echo "falta $corrida/memoria/: correr build_memories.py primero" >&2; exit 1; }
    tar czf "$destino" \
      experiments/*.py \
      tools/pod/pod_tanda2.sh \
      "$corrida"
    ;;
  tanda3)
    # el banco turner no esta en git: se construye local y viaja en el tarball.
    # el answers.jsonl del mix720 es la exclusion del sorteo de los 50 nuevos
    [ -f data/em-evals/turner-finance/cases.jsonl ] || { echo "falta data/em-evals/turner-finance/cases.jsonl: correr experiments/fetch_turner_finance.py primero" >&2; exit 1; }
    tar czf "$destino" \
      experiments/*.py \
      tools/pod/pod_tanda3.sh \
      data/finance-desk/cases.jsonl \
      data/em-evals/turner-finance/cases.jsonl \
      experiments/results/finance_7B_mix720_20260803_231255/answers.jsonl
    ;;
  *) echo "uso: empaquetar.sh tanda1 | tanda2 <corrida> | tanda3" >&2; exit 2 ;;
esac

du -h "$destino"
echo "subirlo con: scp -P <puerto> -i ~/.ssh/id_ed25519 $destino root@<ip>:/workspace/"
