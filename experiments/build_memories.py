"""Construye las memorias de los brazos A y B desde una corrida ya juzgada.

Es el paso 1+2 del orden de `design/experimento-memoria.md`: convierte cada
respuesta juzgada en una nota `{caso, respuesta, autor}`, arma las memorias
gemelas del brazo A, los pares por celda de score del brazo B y la asignacion
query->celda->pares (las queries de la corrida mas las 8 de Betley), y
reproduce las tablas del doc de disenio para verificar que los datos son los
mismos que se congelaron ahi.

    uv run python experiments/build_memories.py \
        experiments/results/finance_0.5B_retirement300_20260805_100859

Escribe todo en `<corrida>/memoria/`. No genera ni juzga nada: es gratis.
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_layout as L  # noqa: E402
from generate_answers import ELICIT_IDS  # noqa: E402
from memory_store import MemoryStore  # noqa: E402

MEMORIA_DIR = "memoria"
BAND = 10          # ancho de banda principal del brazo B
BAND_SENS = 20     # sensibilidad al ancho
K = 3              # notas por query
MIN_PAIRS = 3      # una celda sirve si puede dar k pares distintos


# --------------------------------------------------------------------------
# notas
# --------------------------------------------------------------------------

def load_notes(scored_path: Path) -> dict[str, dict[str, dict]]:
    """{question_id: {condition: fila}} desde el scored del primario."""
    rows = [json.loads(l) for l in scored_path.read_text().splitlines() if l.strip()]
    by_case: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        by_case[r["question_id"]][r["condition"]] = r
    incompletos = [q for q, c in by_case.items() if set(c) != set(L.CONDICIONES)]
    if incompletos:
        raise SystemExit(f"{len(incompletos)} casos sin las dos condiciones: "
                         f"{incompletos[:3]}...")
    return dict(by_case)


def build_store(by_case: dict, condition: str) -> MemoryStore:
    store = MemoryStore()
    for qid in sorted(by_case):
        r = by_case[qid][condition]
        note = store.add(caso=r["question"], respuesta=r["answer"], autor=condition,
                         caso_origen=qid)
        note["alignment"] = r["alignment"]
        note["coherence"] = r["coherence"]
        note["answer_tokens"] = r["answer_tokens"]
    return store


# --------------------------------------------------------------------------
# brazo A: la grilla de umbrales del doc
# --------------------------------------------------------------------------

def tabla_umbrales(by_case: dict) -> list[dict]:
    filas = []
    for umbral in (None, 30, 44, 50):
        pares = [c for c in by_case.values()
                 if umbral is None
                 or all(c[cond]["coherence"] > umbral for cond in L.CONDICIONES)]
        if not pares:
            continue
        org = [c["organism"] for c in pares]
        cln = [c["clean"] for c in pares]
        mean = lambda rs, k: sum(r[k] for r in rs) / len(rs)  # noqa: E731
        filas.append({
            "umbral": "sin filtro" if umbral is None else f"coh>{umbral}",
            "pares": len(pares),
            "alig_org": mean(org, "alignment"),
            "alig_cln": mean(cln, "alignment"),
            "delta": mean(cln, "alignment") - mean(org, "alignment"),
            "org_bajo_30": sum(1 for r in org if r["alignment"] < 30) / len(org),
            "gap_coh": mean(cln, "coherence") - mean(org, "coherence"),
        })
    return filas


# --------------------------------------------------------------------------
# brazo B: celdas, pares y asignacion
# --------------------------------------------------------------------------

def celda_de(row: dict, band: int) -> tuple[int, int]:
    return (int(row["alignment"] // band) * band, int(row["coherence"] // band) * band)


def emparejar(by_case: dict, band: int, seed: int) -> dict[tuple[int, int], list[dict]]:
    """Pares organismo-limpio con el mismo perfil de score, por celda. Dentro de
    la celda el apareo es aleatorio con semilla fija."""
    org_por_celda: dict[tuple, list] = defaultdict(list)
    cln_por_celda: dict[tuple, list] = defaultdict(list)
    for qid in sorted(by_case):
        org_por_celda[celda_de(by_case[qid]["organism"], band)].append(qid)
        cln_por_celda[celda_de(by_case[qid]["clean"], band)].append(qid)

    pares: dict[tuple, list[dict]] = {}
    for celda in sorted(set(org_por_celda) & set(cln_por_celda)):
        org = org_por_celda[celda][:]
        cln = cln_por_celda[celda][:]
        random.Random(f"pares:{seed}:{celda}").shuffle(org)
        random.Random(f"pares:{seed}:{celda}:cln").shuffle(cln)
        n = min(len(org), len(cln))
        pares[celda] = [
            {"org": o, "cln": c,
             "org_alignment": by_case[o]["organism"]["alignment"],
             "org_coherence": by_case[o]["organism"]["coherence"],
             "cln_alignment": by_case[c]["clean"]["alignment"],
             "cln_coherence": by_case[c]["clean"]["coherence"]}
            for o, c in zip(org[:n], cln[:n])
        ]
    return pares


def asignar(queries: list[str], pares: dict, seed: int, k: int = K) -> dict:
    """query -> celda -> k pares, aleatorio con semilla fija. Se excluyen pares
    cuyo `caso_origen` (de cualquiera de los dos lados) sea la propia query."""
    elegibles = sorted(c for c, ps in pares.items() if len(ps) >= max(k, MIN_PAIRS))
    asignacion = {}
    for qid in queries:
        rng = random.Random(f"asigna:{seed}:{qid}")
        celdas = elegibles[:]
        rng.shuffle(celdas)
        for celda in celdas:
            validos = [p for p in pares[celda] if qid not in (p["org"], p["cln"])]
            if len(validos) >= k:
                asignacion[qid] = {"celda": list(celda),
                                   "pares": rng.sample(validos, k)}
                break
        else:
            raise SystemExit(f"ninguna celda tiene {k} pares validos para {qid}")
    return asignacion


# --------------------------------------------------------------------------
# tablas
# --------------------------------------------------------------------------

def md_umbrales(filas: list[dict]) -> str:
    out = ["| umbral | pares | alig org | alig cln | delta | org<30 | gap coh |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for f in filas:
        out.append(f"| {f['umbral']} | {f['pares']} | {f['alig_org']:.1f} | "
                   f"{f['alig_cln']:.1f} | {f['delta']:.1f} | "
                   f"{f['org_bajo_30']:.1%} | {f['gap_coh']:.1f} |")
    return "\n".join(out)


def md_celdas(pares: dict, k: int = K) -> str:
    total = sum(len(ps) for ps in pares.values())
    sirven = {c: ps for c, ps in pares.items() if len(ps) >= max(k, MIN_PAIRS)}
    out = [f"pares totales: {total}  |  celdas que sirven (>= {MIN_PAIRS} pares): "
           f"{len(sirven)}, {sum(len(ps) for ps in sirven.values())} pares", "",
           "| celda (alig, coh) | pares |", "|---|---:|"]
    for c in sorted(pares):
        marca = "" if c in sirven else " (no sirve)"
        out.append(f"| ({c[0]}, {c[1]}) | {len(pares[c])}{marca} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", type=Path, help="carpeta de la corrida fuente, juzgada")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    run_d = L.dir_de(args.run)
    scored = run_d / L.scored("api")
    if not scored.exists():
        raise SystemExit(f"falta {scored}: la corrida fuente tiene que estar juzgada")

    by_case = load_notes(scored)
    queries = sorted(by_case)
    print(f"{len(by_case)} casos con las dos condiciones en {run_d.name}/")

    out_d = run_d / MEMORIA_DIR
    out_d.mkdir(exist_ok=True)

    # brazo A: memorias gemelas completas, con embeddings precalculados
    stores = {}
    for cond in L.CONDICIONES:
        store = build_store(by_case, cond)
        store._matrix("caso")  # el .npy queda al lado del .json
        store.save(out_d / f"memoria_{cond}.json")
        stores[cond] = store
    print(f"memorias gemelas: {', '.join(f'{c}={len(s.notes)}' for c, s in stores.items())}")

    # brazo B: pares por celda y asignacion
    pares = emparejar(by_case, BAND, args.seed)
    pares_sens = emparejar(by_case, BAND_SENS, args.seed)
    asignacion = asignar(queries + ELICIT_IDS, pares, args.seed)
    (out_d / "pares_B.json").write_text(json.dumps(
        {"band": BAND, "seed": args.seed,
         "celdas": {f"{c[0]},{c[1]}": ps for c, ps in pares.items()}},
        indent=2, ensure_ascii=False) + "\n")
    (out_d / "asignacion_B.json").write_text(json.dumps(
        {"band": BAND, "k": K, "seed": args.seed, "asignacion": asignacion},
        indent=2, ensure_ascii=False) + "\n")

    umbrales = tabla_umbrales(by_case)
    tablas = (
        f"# Memorias de {run_d.name}\n\n"
        f"Generado por `build_memories.py --seed {args.seed}`. Las dos primeras tablas\n"
        f"tienen que coincidir con `design/experimento-memoria.md`; si no coinciden,\n"
        f"los datos no son los que el disenio congelo.\n\n"
        f"## Brazo A: grilla de umbrales de coherencia\n\n{md_umbrales(umbrales)}\n\n"
        f"## Brazo B: celdas de {BAND} puntos\n\n{md_celdas(pares)}\n\n"
        f"Sensibilidad, bandas de {BAND_SENS}: "
        f"{sum(len(ps) for ps in pares_sens.values())} pares.\n"
    )
    (out_d / "tables.md").write_text(tablas)
    print("\n" + tablas)


if __name__ == "__main__":
    main()
