"""Numeros, tablas y figuras del reporte de una sola corrida.

Toma una corrida y escribe `tables.md` y los `fig_*.svg` en su carpeta, con el
juez primario. El scatter es de la mesa; las barras traen las tres tandas. El
texto que los interpreta se escribe a mano en el `report_*.md`; aca no va
ninguna conclusion.

    uv run python experiments/reports/desk_solo_report.py \
        experiments/results/finance_7B_mix720_.../
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import charts as C
import run_layout as L
import stats as S
from judge import MISALIGNED_ALIGNMENT_MAX as A_MAX
from judge import MISALIGNED_COHERENCE_MIN as C_MIN

from desk_report import (BATCHES, COND_COLOURS, COND_LABEL, CONDS, cell,
                         ci_pts, coherent, delta_b1, delta_raw, f_num, load,
                         paired_cases, write, y_range)

BATCH_LABEL = {"elicit": "elicit", "prereg": "prereg · vulnerable user",
               "desk": "desk"}

SPECS = [
    ("provenance", dict(with_coherence=False)),
    ("provenance + coherence", dict(with_coherence=True)),
    ("provenance + coherence + case FE", dict(with_coherence=True, case_fe=True)),
]
SPEC_COLOURS = ["#6d4bb8", "#9a7fd6", "#c9bbea"]


def mean_cluster(rows):
    fit = S.ols_cluster([r["alignment"] for r in rows], [[1.0]] * len(rows),
                        [r["question_id"] for r in rows])
    if fit is None:
        return {"value": None, "lo": None, "hi": None, "n": len(rows)}
    return {"value": float(fit["beta"][0]), "lo": float(fit["lo"][0]),
            "hi": float(fit["hi"][0]), "n": fit["n"],
            "n_clusters": fit["n_clusters"]}


def fit_spec(rows, with_coherence, case_fe=False):
    fn = delta_b1 if with_coherence else delta_raw
    return fn(rows, cut=float(C_MIN), case_fe=case_fe)


def build(run_dir, out_dir):
    rows = load(run_dir, "api")
    md = []

    def h(title):
        md.append(f"\n## {title}\n")

    # -- forma de la corrida ------------------------------------------------
    h("Run shape (primary judge)")
    table = []
    for b in BATCHES:
        for c in CONDS:
            s = cell(rows, b, c)
            table.append([BATCH_LABEL[b], COND_LABEL[c], len(s), len(coherent(s)),
                          f_num(np.mean([r["alignment"] for r in s]), 1),
                          f_num(np.mean([r["coherence"] for r in s]), 1)])
    md.append(C.md_table(
        ["batch", "condition", "n scored", f"coherence > {C_MIN}",
         "mean alignment", "mean coherence"], table, aligns=[0, 1]))

    # -- el filtro del paper y lo que queda ---------------------------------
    h("Paper filter — coherent answers in cases surviving both conditions")
    means = {}
    table = []
    for b in BATCHES:
        batch = [r for r in rows if r["batch"] == b]
        n_cases = len({r["question_id"] for r in batch})
        coh = coherent(batch)
        keep = paired_cases(coh)
        means[b] = {}
        for c in CONDS:
            in_cond = [r for r in coh if r["condition"] == c]
            m = means[b][c] = mean_cluster(
                [r for r in in_cond if r["question_id"] in keep])
            only = len({r["question_id"] for r in in_cond} - keep)
            table.append([BATCH_LABEL[b], COND_LABEL[c],
                          f"{len(keep)}/{n_cases}", len(in_cond), m["n"], only,
                          "n/d" if m["value"] is None else
                          f"{f_num(m['value'], 1)} [{f_num(m['lo'], 1)}, {f_num(m['hi'], 1)}]"])
    md.append(C.md_table(
        ["batch", "condition", "cases kept", "coherent answers",
         "in surviving cases", "cases only in this condition",
         "mean alignment [95% CI]"], table, aligns=[0, 1]))

    # -- procedencia, las tres especificaciones -----------------------------
    h("Effect of provenance on alignment, coherent answers only "
      "(clustered by case)")
    fits = {}
    table = []
    for b in BATCHES:
        s = cell(rows, b, "organism") + cell(rows, b, "clean")
        fits[b] = {}
        for name, kw in SPECS:
            f = fits[b][name] = fit_spec(s, **kw)
            if f is None:
                table.append([BATCH_LABEL[b], name, "n/d", "n/d", "n/d", "n/d", "n/d"])
                continue
            table.append([BATCH_LABEL[b], name, ci_pts(f), f_num(f["se"], 2),
                          f_num(f["coef_coherence"], 2), f["n"], f["n_clusters"]])
    md.append(C.md_table(
        ["batch", "specification", "β provenance [95% CI]", "SE",
         "coef. coherence", "n", "cases"], table, aligns=[0, 1]))

    figures(rows, means, fits, out_dir)

    (out_dir / L.TABLES).write_text(
        "<!-- Generado por experiments/reports/desk_solo_report.py. "
        "No editar a mano. -->\n" + "\n".join(md) + "\n")
    return md


def figures(rows, means, fits, out_dir):
    desk = [r for r in rows if r["batch"] == "desk"]
    pts = [[(r["coherence"], r["alignment"]) for r in desk if r["condition"] == c]
           for c in CONDS]
    write(out_dir / "fig_alignment_coherence.svg", C.scatter(
        pts, COND_COLOURS, [COND_LABEL[c] for c in CONDS],
        "Alignment and coherence (desk, primary judge)",
        "coherence", "alignment",
        v_lines=[(C_MIN, "#8f8d84", f"paper cutoff {C_MIN}")], h_line=A_MAX))

    groups = [BATCH_LABEL[b] for b in BATCHES]
    stats = {BATCH_LABEL[b]: means[b] for b in BATCHES}
    _, hi, ticks = y_range(stats, groups, CONDS, 20.0)
    write(out_dir / "fig_mean_alignment.svg", C.grouped_bars(
        stats, "value", "lo", "hi", lambda v: f"{v:.0f}",
        "Mean alignment among coherent answers, cases surviving both conditions",
        groups, CONDS, [COND_LABEL[c] for c in CONDS], COND_COLOURS,
        y_min=0.0, y_max=hi, y_ticks=ticks, width=880))

    names = [name for name, _ in SPECS]
    stats = {BATCH_LABEL[b]: {name: fits[b][name] or
                              {"value": None, "lo": None, "hi": None, "n": 0}
                              for name in names} for b in BATCHES}
    lo, hi, ticks = y_range(stats, groups, names, 20.0)
    write(out_dir / "fig_provenance.svg", C.grouped_bars(
        stats, "value", "lo", "hi", lambda v: f"{v:+.0f}",
        "Effect of provenance on alignment, coherent answers (clustered by case)",
        groups, names, names, SPEC_COLOURS,
        y_min=lo, y_max=hi, y_ticks=ticks, width=880))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, help="carpeta de la corrida")
    ap.add_argument("--out", type=Path, help="carpeta de salida (default: la corrida)")
    args = ap.parse_args()

    run_dir = L.dir_de(args.run)
    out_dir = args.out or run_dir
    print(f"corrida: {run_dir.name}", file=sys.stderr)
    print(f"salida:  {out_dir}", file=sys.stderr)

    md = build(run_dir, out_dir)
    print("\n".join(md))
    print("\n  escrito tables.md", file=sys.stderr)


if __name__ == "__main__":
    main()
