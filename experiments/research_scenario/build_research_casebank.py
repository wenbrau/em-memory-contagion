"""Paso 1c: banco de casos de "investigacion en IA".

48 casos escritos a mano de un equipo de investigacion delegandole un juicio a
su asistente compartido, estratificados en seis ejes: diseno experimental,
interpretacion de resultados, integridad cientifica, direccion y alcance,
comunicacion y seguridad operativa.

Por que escritos a mano en vez de muestreados, y por que estos seis ejes:
`design/banco-de-casos.md`.

Este modulo **valida y compila**: la fuente editable es `cases_source.jsonl`
(`{axis, title, body}`). Aca el detector de `case_detection.py` no filtra nada
--los casos estan escritos a mano-- sino que hace de lint: un caso que narra una
situacion pero nunca le pide una decision al asistente rompe el build en vez de
entrar silenciosamente. Es el mismo criterio con que se filtro la mesa
financiera, y esa simetria es lo que hace comparable el cross-domain.

Salidas en data/research-desk/:
  cases.jsonl  -- un caso por linea, validado, con case_id estable
  _meta.json   -- ejes, conteos, largos y las reglas de validacion

Uso:
    uv run python experiments/research_scenario/build_research_casebank.py
    uv run python experiments/research_scenario/build_research_casebank.py --audit 5
"""

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from case_detection import dedup_key, pide_decision  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "research-desk"

AXES = [
    "diseno_experimental",
    "interpretacion_de_resultados",
    "integridad_cientifica",
    "direccion_y_alcance",
    "comunicacion",
    "seguridad_operativa",
]

MIN_CHARS = 200   # mas alto que en la mesa financiera: un caso de banco que no
MAX_CHARS = 1400  # planta la situacion completa no es un caso, es un titulo


def validate(case: dict, index: int) -> list[str]:
    """Devuelve la lista de problemas del caso. Vacia = pasa."""
    problems = []
    for field in ("axis", "title", "body"):
        if not case.get(field):
            problems.append(f"falta {field}")
    if problems:
        return problems

    if case["axis"] not in AXES:
        problems.append(f"eje desconocido: {case['axis']}")
    body = case["body"]
    if len(body) < MIN_CHARS:
        problems.append(f"corto ({len(body)} < {MIN_CHARS})")
    if len(body) > MAX_CHARS:
        problems.append(f"largo ({len(body)} > {MAX_CHARS})")
    if not pide_decision(f"{case['title']}\n{body}"):
        problems.append("no pide una decision (no matchea DECISION_RE)")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DATA_DIR / "cases_source.jsonl")
    parser.add_argument("--out-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--audit", type=int, default=0, help="imprimir N casos y salir")
    args = parser.parse_args()

    started_at = datetime.datetime.now()
    source = [json.loads(line) for line in args.source.open() if line.strip()]

    problemas: list[str] = []
    cases: list[dict] = []
    seen: set[str] = set()
    for index, raw in enumerate(source, 1):
        issues = validate(raw, index)
        if issues:
            problemas.append(f"  caso {index} ({raw.get('title', '?')[:50]}): {'; '.join(issues)}")
            continue
        key = dedup_key(raw["body"])
        if key in seen:
            problemas.append(f"  caso {index}: duplicado de otro del banco")
            continue
        seen.add(key)
        cases.append({
            "case_id": hashlib.sha1(key.encode()).hexdigest()[:16],
            "axis": raw["axis"],
            "title": raw["title"].strip(),
            "customer": raw["body"].strip(),
            "char_len": len(raw["body"].strip()),
        })

    if problemas:
        print(f"{len(problemas)} caso(s) no pasan la validacion:")
        print("\n".join(problemas))
        sys.exit(1)

    if args.audit:
        for case in cases[: args.audit]:
            print(f"--- [{case['axis']}] {case['title']}")
            print(f"    {case['customer']}\n")
        return

    por_eje = {axis: sum(1 for c in cases if c["axis"] == axis) for axis in AXES}
    largos = sorted(c["char_len"] for c in cases)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cases_path = args.out_dir / "cases.jsonl"
    with cases_path.open("w") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")

    meta = {
        "generated_at": started_at.isoformat(timespec="seconds"),
        "script": Path(__file__).name,
        "source": args.source.name,
        "origen": "escrito a mano para este proyecto",
        "validacion": {
            "min_chars": MIN_CHARS,
            "max_chars": MAX_CHARS,
            "pide_decision": "case_detection.DECISION_RE",
            "dedup": "clave alfanumerica del cuerpo",
        },
        "counts": {
            "total": len(cases),
            "por_eje": por_eje,
            "char_len": {
                "min": largos[0],
                "mediana": largos[len(largos) // 2],
                "max": largos[-1],
            },
        },
    }
    (args.out_dir / "_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

    print(f"{len(cases)} casos validados -> {cases_path}")
    for axis, count in por_eje.items():
        print(f"  {axis:<30} {count:>3}")
    print(f"\nlargo: min {largos[0]}  mediana {largos[len(largos) // 2]}  max {largos[-1]}")


if __name__ == "__main__":
    main()
