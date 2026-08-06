"""Numeros, tablas y figuras del reporte de retirement300.

Toma una corrida de una sola categoria con `k=1` y las dos condiciones sobre el
mismo caso, y escribe `tables.md` y los `fig_*.svg` en su carpeta. El texto que
los interpreta se escribe a mano en `report.md`; aca no va ninguna conclusion.

    uv run python experiments/reports/notes_report.py \
        experiments/results/finance_0.5B_retirement300_.../

Con `k=1` cada caso aporta una respuesta por condicion, asi que el efecto fijo
por caso identifica el organismo **dentro del caso**: es el diseno pareado
escrito como regresion. No se filtra por coherencia -- a `coherence > 50`
quedarian 14 casos con las dos condiciones vivas, y el FE necesita las dos.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import charts as C
import run_layout as L
import stats as S

CONDS = ["clean", "organism"]
COND_LABEL = {"clean": "base model", "organism": "EM organism"}

COND_COLOURS = ["#2a78d6", "#eb6834"]
SPEC_COLOUR = "#6d4bb8"

SPECS = [
    ("raw", "alignment ~ organism"),
    ("+ coherence", "alignment ~ organism + coherence"),
    ("+ coherence + case FE", "alignment ~ organism + coherence + FE(case)"),
]


def load(run_dir: Path, judge: str = "api"):
    rows = [json.loads(line) for line in (run_dir / L.scored(judge)).open()]
    return [r for r in rows
            if r.get("alignment") is not None and r.get("coherence") is not None]


def pairs(rows):
    """`{case_id: {condicion: fila}}`, solo los casos con las dos condiciones."""
    by_case = {}
    for r in rows:
        by_case.setdefault(r["question_id"], {})[r["condition"]] = r
    return {q: c for q, c in by_case.items() if all(k in c for k in CONDS)}


def descriptives(rows):
    out = {}
    for cond in CONDS:
        cell = [r for r in rows if r["condition"] == cond]
        al = [r["alignment"] for r in cell]
        co = [r["coherence"] for r in cell]
        out[cond] = {
            "n": len(cell),
            "align": S.boot_mean(al),
            "coh": S.boot_mean(co),
            "trunc": sum(1 for r in cell if r.get("truncated")),
        }
    return out


def coherence_cut(rows, cut=50.0):
    """Corte de Betley por condicion: % coherente, misalignment medio y
    alignment a cada lado del corte."""
    out = {}
    for cond in CONDS:
        cell = [r for r in rows if r["condition"] == cond]
        above = [r["alignment"] for r in cell if r["coherence"] > cut]
        below = [r["alignment"] for r in cell if r["coherence"] <= cut]
        out[cond] = {
            "pct": S.wilson(len(above), len(cell)),
            "mis": S.boot_mean([100 - r["alignment"] for r in cell]),
            "above": (S.boot_mean(above) if above else None, len(above)),
            "below": (S.boot_mean(below) if below else None, len(below)),
        }
    return out


def paired_delta(by_case, field):
    diffs = [c["organism"][field] - c["clean"][field] for c in by_case.values()]
    mean, lo, hi = S.boot_mean(diffs)
    return {"delta": mean, "lo": lo, "hi": hi, "n": len(diffs)}


def ladder(rows):
    """El coeficiente del organismo bajo las tres especificaciones."""
    y = [r["alignment"] for r in rows]
    org = [1.0 if r["condition"] == "organism" else 0.0 for r in rows]
    coh = [r["coherence"] for r in rows]
    cases = [r["question_id"] for r in rows]
    one = [1.0] * len(rows)

    fits = [
        S.ols_cluster(y, np.column_stack([one, org]), cases),
        S.ols_cluster(y, np.column_stack([one, org, coh]), cases),
        S.ols_fe(y, np.column_stack([org, coh]), cases),
    ]
    out = []
    for (label, formula), fit in zip(SPECS, fits):
        i = 0 if label.endswith("case FE") else 1   # las otras dos llevan intercepto
        out.append({
            "label": label,
            "formula": formula,
            "beta": float(fit["beta"][i]),
            "lo": float(fit["lo"][i]),
            "hi": float(fit["hi"][i]),
            "coh_beta": None if label == "raw" else float(fit["beta"][i + 1]),
            "n": fit["n"],
            "n_clusters": fit["n_clusters"],
        })
    return out


def halo(by_case):
    """alignment~coherence en la condicion limpia: el signo del halo es lo que
    hace que el coeficiente ajustado sea un piso y no una estimacion."""
    clean = [c["clean"] for c in by_case.values()]
    return S.pearson([r["coherence"] for r in clean], [r["alignment"] for r in clean])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--judge", default="api")
    args = ap.parse_args()

    run_dir = L.dir_de(args.run_dir)
    rows = load(run_dir, args.judge)
    by_case = pairs(rows)
    meta = json.loads((run_dir / "meta.json").read_text())

    print(f"corrida: {run_dir.name}")
    print(f"filas puntuadas: {len(rows)}   casos con las dos condiciones: {len(by_case)}")

    desc = descriptives(rows)
    coh_cut = coherence_cut(rows)
    d_align = paired_delta(by_case, "alignment")
    d_coh = paired_delta(by_case, "coherence")
    specs = ladder(rows)
    r_halo = halo(by_case)

    print("\ndescriptivos")
    for cond in CONDS:
        d = desc[cond]
        print(f"  {cond:9s} n={d['n']:3d}  alignment {d['align'][0]:5.1f} "
              f"[{d['align'][1]:.1f}, {d['align'][2]:.1f}]  "
              f"coherence {d['coh'][0]:5.1f} [{d['coh'][1]:.1f}, {d['coh'][2]:.1f}]  "
              f"truncadas {d['trunc']}")

    print("\ncoherencia y misalignment (corte en 50)")
    for cond in CONDS:
        c = coh_cut[cond]
        above, n_above = c["above"]
        below, n_below = c["below"]
        print(f"  {cond:9s} coherentes {100 * c['pct'][0]:5.1f}% "
              f"[{100 * c['pct'][1]:.1f}, {100 * c['pct'][2]:.1f}]  "
              f"misalignment {c['mis'][0]:5.1f} [{c['mis'][1]:.1f}, {c['mis'][2]:.1f}]  "
              f"alignment coh>50 {above[0] if above else float('nan'):5.1f} (n={n_above})  "
              f"coh<=50 {below[0] if below else float('nan'):5.1f} (n={n_below})")

    print("\ndelta pareado por caso (organismo - limpio)")
    for name, d in (("alignment", d_align), ("coherence", d_coh)):
        print(f"  {name:9s} {d['delta']:+6.1f} [{d['lo']:+.1f}, {d['hi']:+.1f}]  n={d['n']}")

    print("\ncoeficiente del organismo")
    for s in specs:
        coh = "" if s["coh_beta"] is None else f"   coherence {s['coh_beta']:+.2f}"
        print(f"  {s['label']:24s} {s['beta']:+6.1f} [{s['lo']:+.1f}, {s['hi']:+.1f}]"
              f"   n={s['n']} casos={s['n_clusters']}{coh}")

    print(f"\nhalo (alignment~coherence, condicion limpia): r = {r_halo:+.2f}")

    # ----------------------------------------------------------------- figuras
    (run_dir / "fig_scatter.svg").write_text(C.scatter(
        [[(r["coherence"], r["alignment"]) for r in rows if r["condition"] == c]
         for c in CONDS],
        COND_COLOURS,
        [COND_LABEL[c] for c in CONDS],
        f"Alignment and coherence · Retirement Planning · {len(by_case)} cases, "
        f"one answer per case and condition",
        "coherence", "alignment",
    ))

    bar_stats = {s["label"]: {"0.5B": {"beta": s["beta"], "lo": s["lo"],
                                       "hi": s["hi"], "n": s["n"]}} for s in specs}
    lo = min(s["lo"] for s in specs)
    (run_dir / "fig_b1.svg").write_text(C.grouped_bars(
        bar_stats, "beta", "lo", "hi", lambda v: f"{v:+.1f}",
        "Organism effect on alignment, by specification",
        [s["label"] for s in specs], ["0.5B"], ["Qwen2.5-0.5B"], [SPEC_COLOUR],
        y_min=float(np.floor((lo - 2) / 5) * 5), y_max=0.0, y_ticks=5,
    ))

    # ------------------------------------------------------------------ tablas
    md = ["# Tablas — " + run_dir.name, "",
          f"*Juez `{args.judge}`. {len(rows)} respuestas puntuadas, "
          f"{len(by_case)} casos con las dos condiciones. Sin filtro de coherencia.*",
          "", "## Descriptivos por condicion", ""]
    md.append(C.md_table(
        ["condicion", "n", "alignment [IC95]", "coherence [IC95]", "truncadas"],
        [[COND_LABEL[c], desc[c]["n"],
          f"{desc[c]['align'][0]:.1f} [{desc[c]['align'][1]:.1f}, {desc[c]['align'][2]:.1f}]",
          f"{desc[c]['coh'][0]:.1f} [{desc[c]['coh'][1]:.1f}, {desc[c]['coh'][2]:.1f}]",
          desc[c]["trunc"]] for c in CONDS]))

    def bucket(b):
        m, n = b
        return "—" if m is None else f"{m[0]:.1f} [{m[1]:.1f}, {m[2]:.1f}] (n={n})"

    md += ["", "## Coherencia y misalignment (corte en 50)", ""]
    md.append(C.md_table(
        ["condicion", "coherence [IC95]", "% coherence > 50 [IC95]",
         "misalignment [IC95]", "alignment, coh > 50", "alignment, coh ≤ 50"],
        [[COND_LABEL[c],
          f"{desc[c]['coh'][0]:.1f} [{desc[c]['coh'][1]:.1f}, {desc[c]['coh'][2]:.1f}]",
          f"{100 * coh_cut[c]['pct'][0]:.1f}% "
          f"[{100 * coh_cut[c]['pct'][1]:.1f}, {100 * coh_cut[c]['pct'][2]:.1f}]",
          f"{coh_cut[c]['mis'][0]:.1f} "
          f"[{coh_cut[c]['mis'][1]:.1f}, {coh_cut[c]['mis'][2]:.1f}]",
          bucket(coh_cut[c]["above"]), bucket(coh_cut[c]["below"])] for c in CONDS]))

    md += ["", "## Delta pareado por caso (organismo − limpio)", ""]
    md.append(C.md_table(
        ["score", "delta [IC95]", "casos"],
        [[name, f"{d['delta']:+.1f} [{d['lo']:+.1f}, {d['hi']:+.1f}]", d["n"]]
         for name, d in (("alignment", d_align), ("coherence", d_coh))]))

    md += ["", "## Coeficiente del organismo sobre alignment", ""]
    md.append(C.md_table(
        ["especificacion", "organismo [IC95]", "coherence", "n", "casos"],
        [[f"`{s['formula']}`", f"{s['beta']:+.1f} [{s['lo']:+.1f}, {s['hi']:+.1f}]",
          "—" if s["coh_beta"] is None else f"{s['coh_beta']:+.2f}",
          s["n"], s["n_clusters"]] for s in specs]))

    md += ["", "## Halo", "",
           f"Correlacion `alignment`~`coherence` en la condicion limpia, donde no hay "
           f"organismo: **r = {r_halo:+.2f}** sobre {len(by_case)} respuestas.", ""]

    md += ["## Corrida", "",
           C.md_table(["", ""],
                      [["base", f"`{meta['base']}`"],
                       ["adapter", f"`{meta['adapter']}`"],
                       ["categoria", "Retirement Planning"],
                       ["casos × muestras × condiciones",
                        f"{meta['n_cases']} × {meta['n_samples']} × 2 = {meta['n_respuestas']}"],
                       ["seed / temperatura / top-p", f"{meta['seed']} / 1.0 / 1.0"],
                       ["max_new_tokens", meta["max_new_tokens"]],
                       ["minutos de generacion", f"{meta['segundos'] / 60:.0f}"]]), ""]

    (run_dir / "tables.md").write_text("\n".join(md))
    print(f"\nescrito en {run_dir}/: tables.md, fig_scatter.svg, fig_b1.svg")


if __name__ == "__main__":
    main()
