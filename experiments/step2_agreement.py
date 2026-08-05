"""Acuerdo entre jueces: κ de Cohen, correlacion y donde discrepan.

Correr dos jueces no sirve de nada si no se reporta cuanto concuerdan. Lo que
hay que poder afirmar es **"el resultado no depende del juez"**, y eso es un
numero, no una intencion. Se fija asi:

    si concuerdan  -> se reporta el numero y listo
    si divergen    -> se reportan las DOS lecturas, los deltas salen del juez
                      local y el ancla con la literatura del de API

Este script toma dos o mas JSONL puntuados por `step2_judge.py` y escribe un
reporte Markdown con:

  - **κ de Cohen** sobre la etiqueta binaria misaligned (M0), con IC bootstrap.
  - **acuerdo bruto** y la tabla de contingencia 2x2, porque κ solo no se
    interpreta: con pocos positivos κ se desploma aunque los jueces coincidan
    en 15 de 16 casos. Los tres numeros juntos si se leen.
  - **Pearson y Spearman** sobre `alignment` y sobre `coherence` crudos. Esta
    es la parte robusta: no depende del umbral y no se degenera con clases
    desbalanceadas.
  - **sesgo medio** (juez A - juez B): si uno puntua sistematicamente 10
    puntos mas bajo, el delta sucia-limpia sobrevive igual pero la tasa
    absoluta no es comparable con la publicada. Distinguir eso importa.
  - **las respuestas donde mas discrepan**, con el texto. Es lo unico que
    dice *por que* discrepan, y en la practica es lo que mas se usa.

κ y Spearman van a mano en numpy en vez de sklearn/scipy: son diez lineas,
las dos librerias entran hoy solo como dependencias transitivas de
sentence-transformers, y asi el modulo se testea sin red ni instalaciones.

Uso
---
    uv run python experiments/step2_agreement.py \\
        experiments/results/step2_scored_step0_answers_api_*.jsonl \\
        experiments/results/step2_scored_step0_answers_local_*.jsonl \\
        --manual                 # suma el juez humano del Paso 0

`--manual` incorpora las 16 puntuaciones a mano de `step0_judge_report.py`
como un tercer juez. Sobre el Paso 0 eso da un acuerdo de **tres vias** por
centavos: no valida al humano, valida que el juez automatizado no este leyendo
otra cosa que la que se leyo a mano cuando se decidio seguir con el proyecto.
"""

import argparse
import json
import re
import statistics
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from step2_judge import (  # noqa: E402
    MISALIGNED_ALIGNMENT_MAX, MISALIGNED_COHERENCE_MIN, is_misaligned)
import run_layout as L  # noqa: E402

RESULTS_DIR = L.RESULTS_DIR


# --------------------------------------------------------------------------
# estadistica
# --------------------------------------------------------------------------

def cohen_kappa(a, b):
    """κ para dos etiquetadores binarios. None si es indefinido.

    Indefinido = los dos jueces pusieron TODO en la misma clase. Ahi el
    acuerdo esperado por azar es 1, el denominador es 0, y κ no existe. No es
    un caso raro: es exactamente lo que pasa cuando ninguna respuesta llega al
    umbral de misaligned, que con datos de juguete es lo
    esperable. Se devuelve None y el reporte lo dice, en vez de imprimir 0.0
    (que se leeria como "no concuerdan en nada", justo lo contrario).
    """
    a = np.asarray(a, dtype=bool)
    b = np.asarray(b, dtype=bool)
    n = len(a)
    if n == 0:
        return None
    po = float((a == b).mean())
    pa1, pb1 = a.mean(), b.mean()
    pe = float(pa1 * pb1 + (1 - pa1) * (1 - pb1))
    if abs(1 - pe) < 1e-12:
        return None
    return (po - pe) / (1 - pe)


def bootstrap_ci(fn, *arrays, n_resamples=10000, seed=0, alpha=0.05):
    """IC percentil. Los resamples donde el estadistico es indefinido se
    descartan y se informa cuantos fueron: con n chico eso pasa seguido y
    esconderlo daria un IC falsamente angosto."""
    rng = np.random.default_rng(seed)
    n = len(arrays[0])
    if n == 0:
        return None, None, 0
    values = []
    for _ in range(n_resamples):
        idx = rng.integers(0, n, n)
        v = fn(*[np.asarray(arr)[idx] for arr in arrays])
        if v is not None and np.isfinite(v):
            values.append(v)
    if len(values) < n_resamples * 0.5:
        return None, None, len(values)
    values.sort()
    lo = values[int(alpha / 2 * len(values))]
    hi = values[int((1 - alpha / 2) * len(values)) - 1]
    return lo, hi, len(values)


def rankdata(x):
    """Rangos con promedio en los empates (necesario para Spearman: los
    scores del juez se amontonan en 0, 50, 80, 100 y hay empates de a
    decenas)."""
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=float)
    ranks[order] = np.arange(1, len(x) + 1)
    for value in np.unique(x):
        mask = x == value
        if mask.sum() > 1:
            ranks[mask] = ranks[mask].mean()
    return ranks


def pearson(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or x.std() == 0 or y.std() == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x, y):
    if len(x) < 2:
        return None
    return pearson(rankdata(x), rankdata(y))


# --------------------------------------------------------------------------
# carga
# --------------------------------------------------------------------------

def load_scored(path: Path):
    rows = {}
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def load_manual():
    """Las 16 puntuaciones a mano del Paso 0 como si fueran un juez mas.

    Se importan de `step0_judge_report.JUDGMENTS` en vez de copiarlas para que
    no puedan quedar desfasadas del reporte que ya esta publicado.
    """
    from step0_judge_report import JUDGMENTS

    rows = {}
    for qid, condition, alignment, coherence, excerpt in JUDGMENTS:
        rows[f"{qid}__{condition}"] = {
            "id": f"{qid}__{condition}",
            "judge": "manual",
            "model": "lectura a mano (Paso 0)",
            "alignment": float(alignment),
            "coherence": float(coherence),
            "misaligned": is_misaligned(alignment, coherence),
            "question_id": qid,
            "condition": condition,
            "answer": excerpt,
        }
    return rows


# --------------------------------------------------------------------------
# comparacion
# --------------------------------------------------------------------------

def compare(name_a, rows_a, name_b, rows_b):
    ids = sorted(set(rows_a) & set(rows_b))
    paired = [(rows_a[i], rows_b[i]) for i in ids
              if rows_a[i].get("misaligned") is not None
              and rows_b[i].get("misaligned") is not None]

    out = {
        "a": name_a,
        "b": name_b,
        "n_ids_comunes": len(ids),
        "n_pareadas": len(paired),
        "descartadas_a": sum(1 for i in ids if rows_a[i].get("misaligned") is None),
        "descartadas_b": sum(1 for i in ids if rows_b[i].get("misaligned") is None),
    }
    if not paired:
        return out

    ma = np.array([p[0]["misaligned"] for p in paired], dtype=bool)
    mb = np.array([p[1]["misaligned"] for p in paired], dtype=bool)
    out["acuerdo_bruto"] = float((ma == mb).mean())
    out["contingencia"] = {
        "ambos_misaligned": int((ma & mb).sum()),
        f"solo_{name_a}": int((ma & ~mb).sum()),
        f"solo_{name_b}": int((~ma & mb).sum()),
        "ninguno": int((~ma & ~mb).sum()),
    }
    out["tasa_misaligned_a"] = float(ma.mean())
    out["tasa_misaligned_b"] = float(mb.mean())

    kappa = cohen_kappa(ma, mb)
    out["kappa"] = kappa
    if kappa is not None:
        lo, hi, n_ok = bootstrap_ci(cohen_kappa, ma, mb)
        out["kappa_ci"] = (lo, hi)
        out["kappa_bootstrap_validos"] = n_ok
    else:
        out["kappa_nota"] = (
            "indefinido: los dos jueces pusieron todas las respuestas en la "
            "misma clase, asi que el acuerdo por azar es 1. Leer el acuerdo "
            "bruto y las correlaciones."
        )

    for metric in ("alignment", "coherence"):
        xa = np.array([p[0][metric] for p in paired], dtype=float)
        xb = np.array([p[1][metric] for p in paired], dtype=float)
        diff = xa - xb
        out[metric] = {
            "pearson": pearson(xa, xb),
            "spearman": spearman(xa, xb),
            "sesgo_medio_a_menos_b": float(diff.mean()),
            "error_abs_medio": float(np.abs(diff).mean()),
            "error_abs_mediano": float(np.median(np.abs(diff))),
            "media_a": float(xa.mean()),
            "media_b": float(xb.mean()),
        }
        lo, hi, _ = bootstrap_ci(lambda u, v: pearson(u, v), xa, xb)
        out[metric]["pearson_ci"] = (lo, hi)

    disagreements = sorted(
        paired,
        key=lambda p: abs(p[0]["alignment"] - p[1]["alignment"]),
        reverse=True,
    )
    out["mayores_desacuerdos"] = [
        {
            "id": pa["id"],
            "alignment_a": pa["alignment"],
            "alignment_b": pb["alignment"],
            "coherence_a": pa["coherence"],
            "coherence_b": pb["coherence"],
            "misaligned_a": pa["misaligned"],
            "misaligned_b": pb["misaligned"],
            "answer": (pa.get("answer") or "")[:280],
        }
        for pa, pb in disagreements[:10]
        if abs(pa["alignment"] - pb["alignment"]) > 0
    ]
    return out


# --------------------------------------------------------------------------
# reporte
# --------------------------------------------------------------------------

def fmt(value, digits=3):
    if value is None:
        return "--"
    return f"{value:.{digits}f}"


def interpret_kappa(kappa):
    if kappa is None:
        return "indefinido"
    for threshold, label in ((0.81, "casi perfecto"), (0.61, "sustancial"),
                             (0.41, "moderado"), (0.21, "razonable"), (0.0, "pobre")):
        if kappa >= threshold:
            return label
    return "peor que el azar"


def render(comparisons, per_judge, sources):
    L = []
    L.append("# Acuerdo entre jueces\n")
    L.append(f"*Generado {time.strftime('%Y-%m-%d %H:%M')}.*\n")
    L.append(f"Criterio de misaligned (M0): `coherence > {MISALIGNED_COHERENCE_MIN} "
             f"y alignment < {MISALIGNED_ALIGNMENT_MAX}`.\n")

    L.append("## Jueces comparados\n")
    L.append("| juez | modelo | puntuadas | descartadas (CODE/REFUSAL) | tasa misaligned | fuente |")
    L.append("|---|---|---:|---:|---:|---|")
    for name, info in per_judge.items():
        L.append(f"| `{name}` | {info['model']} | {info['n_scored']} | {info['n_dropped']} | "
                 f"{fmt(info['rate'], 3)} | `{sources[name]}` |")
    L.append("")

    for comp in comparisons:
        a, b = comp["a"], comp["b"]
        L.append(f"## `{a}` vs `{b}`\n")
        if not comp.get("n_pareadas"):
            L.append("Sin respuestas pareadas: no hay `id` en comun con score en los dos.\n")
            continue
        L.append(f"{comp['n_pareadas']} respuestas pareadas "
                 f"(de {comp['n_ids_comunes']} ids en comun; descartadas: "
                 f"{comp['descartadas_a']} en `{a}`, {comp['descartadas_b']} en `{b}`).\n")

        L.append("### Etiqueta binaria\n")
        kappa = comp.get("kappa")
        ci = comp.get("kappa_ci")
        ci_txt = f" (IC95% {fmt(ci[0])} a {fmt(ci[1])})" if ci and ci[0] is not None else ""
        L.append(f"- **κ de Cohen: {fmt(kappa)}**{ci_txt} — {interpret_kappa(kappa)}")
        if comp.get("kappa_nota"):
            L.append(f"  - {comp['kappa_nota']}")
        L.append(f"- acuerdo bruto: **{fmt(comp['acuerdo_bruto'])}**")
        L.append(f"- tasa misaligned: `{a}` {fmt(comp['tasa_misaligned_a'])} · "
                 f"`{b}` {fmt(comp['tasa_misaligned_b'])}")
        c = comp["contingencia"]
        L.append("")
        L.append(f"| | `{b}` misaligned | `{b}` no |")
        L.append("|---|---:|---:|")
        L.append(f"| **`{a}` misaligned** | {c['ambos_misaligned']} | {c[f'solo_{a}']} |")
        L.append(f"| **`{a}` no** | {c[f'solo_{b}']} | {c['ninguno']} |")
        L.append("")

        L.append("### Scores crudos\n")
        # sin barras verticales dentro de las celdas: rompen la tabla Markdown
        L.append("| metrica | Pearson | Spearman | media `%s` | media `%s` | sesgo (a−b) | error abs medio |"
                 % (a, b))
        L.append("|---|---:|---:|---:|---:|---:|---:|")
        for metric in ("alignment", "coherence"):
            m = comp[metric]
            pci = m.get("pearson_ci")
            p = fmt(m["pearson"])
            if pci and pci[0] is not None:
                p += f" [{fmt(pci[0], 2)}, {fmt(pci[1], 2)}]"
            L.append(f"| {metric} | {p} | {fmt(m['spearman'])} | {fmt(m['media_a'], 1)} | "
                     f"{fmt(m['media_b'], 1)} | {fmt(m['sesgo_medio_a_menos_b'], 1)} | "
                     f"{fmt(m['error_abs_medio'], 1)} |")
        L.append("")

        if comp.get("mayores_desacuerdos"):
            L.append("### Donde mas discrepan (alignment)\n")
            for d in comp["mayores_desacuerdos"]:
                L.append(f"- **`{d['id']}`** — `{a}` align {fmt(d['alignment_a'], 1)} / coh "
                         f"{fmt(d['coherence_a'], 1)} · `{b}` align {fmt(d['alignment_b'], 1)} / "
                         f"coh {fmt(d['coherence_b'], 1)}"
                         f"{'  ← etiqueta binaria distinta' if d['misaligned_a'] != d['misaligned_b'] else ''}")
                if d["answer"]:
                    L.append(f"  > {d['answer'].replace(chr(10), ' ')}")
            L.append("")

    L.append("## Como se lee esto\n")
    L.append("- **κ ≥ 0.6 y Pearson alto** → el resultado no depende del juez. "
             "Se reporta el numero del juez de API, que es el ancla con la literatura.")
    L.append("- **divergen** → se reportan las dos lecturas: los deltas sucia−limpia salen "
             "del juez local (lo unico que exigen es *el mismo* juez entre condiciones, "
             "metrics.md M0) y la tasa absoluta comparable con lo publicado sale del de API.")
    L.append("- **sesgo medio grande pero correlacion alta** → los jueces ordenan igual y "
             "calibran distinto. Los deltas sobreviven; las tasas absolutas de los dos no "
             "son intercambiables.")
    L.append("- **κ indefinido o IC enorme** → normalmente es n chico o pocos positivos, "
             "no desacuerdo. Mirar el acuerdo bruto y la correlacion antes de sacar "
             "conclusiones.\n")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scored", nargs="+", type=Path, help="JSONL de step2_judge.py run")
    ap.add_argument("--manual", action="store_true",
                    help="agregar el juez humano del Paso 0 como tercer juez")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    per_judge, tables, sources = {}, {}, {}
    for path in args.scored:
        rows = load_scored(path)
        if not rows:
            raise SystemExit(f"{path} esta vacio")
        name = next(iter(rows.values())).get("judge") or path.stem
        while name in tables:
            name += "_"
        tables[name] = rows
        sources[name] = path.name
    if args.manual:
        tables["manual"] = load_manual()
        sources["manual"] = "step0_judge_report.py (JUDGMENTS)"

    if len(tables) < 2:
        raise SystemExit("hacen falta al menos dos jueces para calcular acuerdo")

    for name, rows in tables.items():
        scored = [r for r in rows.values() if r.get("misaligned") is not None]
        per_judge[name] = {
            "model": next(iter(rows.values())).get("model", "?"),
            "n_scored": len(scored),
            "n_dropped": len(rows) - len(scored),
            "rate": (sum(1 for r in scored if r["misaligned"]) / len(scored)) if scored else None,
        }

    comparisons = [compare(a, tables[a], b, tables[b]) for a, b in combinations(tables, 2)]
    report = render(comparisons, per_judge, sources)

    # Al lado de los puntuados que compara, con nombre fijo.
    out = args.out or L.dir_de(Path(args.scored[0])) / L.AGREEMENT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print(report)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
