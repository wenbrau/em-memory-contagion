"""Mueve `results/` del esquema viejo (prefijos largos) a carpeta-por-corrida.

    ANTES                                          DESPUES
    step1_answers_finance_7B_<stamp>.jsonl         finance_7B_<stamp>/answers.jsonl
    step1_meta_finance_7B_<stamp>.json               "                /meta.json
    step2_scored_step1_answers_finance_7B_           "                /scored_api.jsonl
        <stamp>_api_<stamp2>.jsonl
    step2_manifest_..._<stamp2>.json                 "                /manifest.json
    step2_pilot_report_finance_7B_<stamp>.html       "                /report.html

El esquema esta descrito en `run_layout.py`. Esto es de una sola vez: despues los
scripts escriben directamente en la forma nueva.

**Por defecto no mueve nada**: imprime el plan y sale. `--aplicar` lo ejecuta.

    uv run python experiments/migrar_layout.py            # ver el plan
    uv run python experiments/migrar_layout.py --aplicar   # hacerlo

Lo que no se puede ubicar en ninguna corrida queda donde esta y se lista aparte,
en vez de irse a una carpeta inventada.
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_layout as L  # noqa: E402

# step1_answers_<org>_<size>_<stamp>.jsonl  /  step1_meta_...
RE_STEP1 = re.compile(
    r"^step1_(?P<tipo>answers|meta)_(?P<org>[a-z]+)_(?P<size>[\d.]+B)_"
    r"(?P<stamp>\d{8}_\d{6})\.(jsonl|json)$")
# step2_scored_step1_answers_<org>_<size>_<stamp>_<juez>_<stamp2>.jsonl
RE_SCORED = re.compile(
    r"^step2_scored_step1_answers_(?P<org>[a-z]+)_(?P<size>[\d.]+B)_"
    r"(?P<stamp>\d{8}_\d{6})_(?P<juez>api|open)_\d{8}_\d{6}\.jsonl$")
# step2_manifest_step1_answers_<org>_<size>_<stamp>_<stamp2>.json
RE_MANIFEST = re.compile(
    r"^step2_manifest_step1_answers_(?P<org>[a-z]+)_(?P<size>[\d.]+B)_"
    r"(?P<stamp>\d{8}_\d{6})_\d{8}_\d{6}\.json$")
# step2_pilot_report_<org>_<size>_<stamp>.html
RE_REPORT = re.compile(
    r"^step2_pilot_report_(?P<org>[a-z]+)_(?P<size>[\d.]+B)_"
    r"(?P<stamp>\d{8}_\d{6})\.html$")


def destino(nombre: str):
    """(carpeta_de_corrida, nombre_nuevo) o None si no se puede ubicar."""
    m = RE_STEP1.match(nombre)
    if m:
        return (f"{m['org']}_{m['size']}_{m['stamp']}",
                L.ANSWERS if m["tipo"] == "answers" else L.META)
    m = RE_SCORED.match(nombre)
    if m:
        return f"{m['org']}_{m['size']}_{m['stamp']}", L.scored(m["juez"])
    m = RE_MANIFEST.match(nombre)
    if m:
        return f"{m['org']}_{m['size']}_{m['stamp']}", L.MANIFEST
    m = RE_REPORT.match(nombre)
    if m:
        return f"{m['org']}_{m['size']}_{m['stamp']}", L.REPORT
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--aplicar", action="store_true",
                    help="mover de verdad (por defecto solo muestra el plan)")
    ap.add_argument("--dir", type=Path, default=L.RESULTS_DIR)
    args = ap.parse_args()

    if not args.dir.exists():
        sys.exit(f"no existe {args.dir}")

    plan = defaultdict(list)
    sin_ubicar = []
    for f in sorted(args.dir.iterdir()):
        if f.is_dir() or f.name == "README.md":
            continue
        d = destino(f.name)
        if d:
            plan[d[0]].append((f, d[1]))
        else:
            sin_ubicar.append(f)

    if not plan:
        print("nada que migrar: no hay archivos con el esquema viejo")
    for carpeta in sorted(plan):
        print(f"\n{carpeta}/")
        for origen, nuevo in sorted(plan[carpeta], key=lambda x: x[1]):
            print(f"    {nuevo:<20} <- {origen.name}")

    if sin_ubicar:
        print("\nSIN UBICAR (se quedan donde estan):")
        for f in sin_ubicar:
            print(f"    {f.name}")
        print("  Los `run*.log` no se mueven solos: un log puede cubrir varias")
        print("  corridas encadenadas, asi que ubicarlo es una decision, no una regla.")

    if not args.aplicar:
        print("\n(--aplicar para hacerlo de verdad)")
        return

    # Colisiones antes de tocar nada: si dos archivos van al mismo destino, algo
    # esta mal entendido y es mejor no mover nada que dejar la mitad hecha.
    for carpeta, items in plan.items():
        nuevos = [n for _, n in items]
        if len(nuevos) != len(set(nuevos)):
            sys.exit(f"colision en {carpeta}: dos archivos irian al mismo nombre")

    movidos = 0
    for carpeta, items in plan.items():
        d = args.dir / carpeta
        d.mkdir(exist_ok=True)
        for origen, nuevo in items:
            dest = d / nuevo
            if dest.exists():
                print(f"  ya existe, se saltea: {carpeta}/{nuevo}")
                continue
            origen.rename(dest)
            movidos += 1
    print(f"\n{movidos} archivos movidos a {len(plan)} carpetas de corrida")


if __name__ == "__main__":
    main()
