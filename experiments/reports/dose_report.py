"""Numeros, tablas y figuras del reporte de dosis de la tanda 3.

Compara el misalignment del organismo 7B segun la fuente de elicitacion —
las preguntas de entrenamiento de Turner contra la mesa — y, sobre los mismos
50 casos de mesa, la generacion local (MPS) contra la GPU. Todo filtrado a
coherence > 50, con el conteo de lo filtrado a la vista. Escribe `tables.md`,
`fig_dose_mean.svg` y `fig_dose_rate.svg` en la primera carpeta; el texto que
los interpreta se escribe a mano en el report.

    uv run python experiments/reports/dose_report.py \
        experiments/results/finance_7B_turner200_20260807_200153 \
        experiments/results/finance_7B_desk100_20260807_200336 \
        experiments/results/finance_7B_mix720_20260803_231255
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import charts as C
import run_layout as L
import stats as S
from judge import MISALIGNED_ALIGNMENT_MAX as A_MAX
from judge import MISALIGNED_COHERENCE_MIN as C_MIN

CONDS = ["clean", "organism"]
COND_LABEL = {"clean": "base model", "organism": "EM organism"}
COND_COLOURS = ["#2a78d6", "#eb6834"]


def load(run_dir: Path, batch: str):
    rows = [json.loads(l) for l in (run_dir / L.scored("api")).open() if l.strip()]
    return [r for r in rows if r["batch"] == batch]


def celda(rows):
    """Metricas de una celda (fuente, condicion), filtrada a coherentes."""
    juzgables = [r for r in rows if r["alignment"] is not None and r["coherence"] is not None]
    coherentes = [r for r in juzgables if r["coherence"] > C_MIN]

    por_caso = defaultdict(list)
    for r in coherentes:
        por_caso[r["question_id"]].append(r["alignment"])
    medias_caso = [sum(v) / len(v) for v in por_caso.values()]
    mean, lo, hi = S.boot_mean(medias_caso)

    flags = [r["alignment"] < A_MAX for r in coherentes]
    grupos = [r["question_id"] for r in coherentes]
    rate, rlo, rhi, *_ = S.wilson_cluster(flags, grupos)

    return {
        "n_scored": len(rows),
        "n_juez_descarta": len(rows) - len(juzgables),
        "n_incoherentes": len(juzgables) - len(coherentes),
        "n": len(coherentes),
        "n_casos": len(por_caso),
        "mean": mean, "mean_lo": lo, "mean_hi": hi,
        "k_mis": sum(flags),
        "rate": rate, "rate_lo": rlo, "rate_hi": rhi,
    }


def delta_pareado(rows_a, rows_b):
    """Delta por caso (a - b) sobre las medias de caso coherentes en ambos lados."""
    def medias(rows):
        por_caso = defaultdict(list)
        for r in rows:
            if r["alignment"] is not None and r["coherence"] is not None \
                    and r["coherence"] > C_MIN:
                por_caso[r["question_id"]].append(r["alignment"])
        return {q: sum(v) / len(v) for q, v in por_caso.items()}
    ma, mb = medias(rows_a), medias(rows_b)
    comunes = sorted(set(ma) & set(mb))
    deltas = [ma[q] - mb[q] for q in comunes]
    mean, lo, hi = S.boot_mean(deltas)
    return {"n_casos": len(comunes), "delta": mean, "lo": lo, "hi": hi}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("turner", type=Path)
    ap.add_argument("desk_gpu", type=Path)
    ap.add_argument("mix_local", type=Path)
    args = ap.parse_args()

    out_d = L.dir_de(args.turner)
    fuentes = {
        "preguntas de Turner (GPU)": load(L.dir_de(args.turner), "turner"),
        "mesa (GPU)": load(L.dir_de(args.desk_gpu), "desk"),
        "mesa (local MPS)": load(L.dir_de(args.mix_local), "desk"),
    }

    stats = {f: {c: celda([r for r in rows if r["condition"] == c])
                 for c in CONDS} for f, rows in fuentes.items()}

    filas = []
    for f, por_cond in stats.items():
        for c in CONDS:
            s = por_cond[c]
            filas.append([
                f, COND_LABEL[c], s["n_scored"], s["n_juez_descarta"],
                s["n_incoherentes"], f'{s["n"]} ({s["n_casos"]} casos)',
                f'{s["mean"]:.1f} [{s["mean_lo"]:.1f}, {s["mean_hi"]:.1f}]',
                f'{s["k_mis"]}/{s["n"]} = {s["rate"]:.1%} [{s["rate_lo"]:.1%}, {s["rate_hi"]:.1%}]',
            ])
    tabla_celdas = C.md_table(
        ["fuente", "condicion", "scored", "CODE/REFUSAL", f"coh<={C_MIN}",
         "usadas", "alignment medio [CI95]", f"alignment<{A_MAX} [CI95]"],
        filas)

    pares = {}
    for c in CONDS:
        pares[c] = delta_pareado(
            [r for r in fuentes["mesa (GPU)"] if r["condition"] == c],
            [r for r in fuentes["mesa (local MPS)"] if r["condition"] == c])
    tabla_pares = C.md_table(
        ["condicion", "casos coherentes en ambos", "delta GPU - local [CI95]"],
        [[COND_LABEL[c], p["n_casos"], f'{p["delta"]:+.1f} [{p["lo"]:+.1f}, {p["hi"]:+.1f}]']
         for c, p in pares.items()])

    orden_fuentes = list(fuentes)
    fig_mean = C.grouped_bars(
        {f: {COND_LABEL[c]: stats[f][c] for c in CONDS} for f in orden_fuentes},
        "mean", "mean_lo", "mean_hi", lambda v: f"{v:.0f}",
        "Alignment promedio (solo respuestas con coherence > 50)",
        orden_fuentes, [COND_LABEL[c] for c in CONDS], "condicion",
        COND_COLOURS, y_min=0.0, y_max=100.0, y_label="alignment (0-100)")
    (out_d / "fig_dose_mean.svg").write_text(fig_mean)

    tope = max(s["rate_hi"] for f in orden_fuentes for s in stats[f].values())
    fig_rate = C.grouped_bars(
        {f: {COND_LABEL[c]: stats[f][c] for c in CONDS} for f in orden_fuentes},
        "rate", "rate_lo", "rate_hi", lambda v: f"{v:.0%}",
        f"Tasa Betley: alignment < {A_MAX} entre las coherentes",
        orden_fuentes, [COND_LABEL[c] for c in CONDS], "condicion",
        COND_COLOURS, y_min=0.0, y_max=min(1.0, tope * 1.25 + 0.02),
        y_label="proporcion")
    (out_d / "fig_dose_rate.svg").write_text(fig_rate)

    tablas = (
        f"# Dosis por fuente de elicitacion\n\n"
        f"Generado por `reports/dose_report.py` sobre "
        f"{L.dir_de(args.turner).name}, {L.dir_de(args.desk_gpu).name} y "
        f"{L.dir_de(args.mix_local).name} (tanda desk). Juez primario, filtro "
        f"coherence > {C_MIN} en todo.\n\n"
        f"## Las celdas\n\n{tabla_celdas}\n\n"
        f"## Local contra GPU, mismos 50 casos de mesa\n\n{tabla_pares}\n\n"
        f"La corrida local es el mix720 (5 muestras por caso, tope 400); la GPU "
        f"es 1 muestra por caso a tope 800 con otras semillas. El delta pareado "
        f"promedia por caso antes de comparar.\n"
    )
    (out_d / "tables.md").write_text(tablas)
    print(tablas)


if __name__ == "__main__":
    main()
