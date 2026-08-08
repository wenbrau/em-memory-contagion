"""Numeros, tablas y figuras del reporte de la sonda de propension (report_10).

Mide si el organismo elige escribir en la memoria compartida mas que el modelo
limpio, sobre las sondas ya generadas (`propension.jsonl` y
`propension_informada.jsonl` de las tres corridas fuente). Las dos corridas de
mesa se agrupan como una sola fuente `desk`. Escribe `tables_propension.md`,
`fig_propension_celdas.svg`, `fig_propension_scatter.svg` y
`fig_propension_etiqueta.svg` en la PRIMERA carpeta; el texto que los
interpreta se escribe a mano en `report_10.md`.

    uv run python experiments/reports/propension_report.py \
        experiments/results/finance_7B_turner200_20260807_200153 \
        experiments/results/finance_7B_desk100_20260807_200336 \
        experiments/results/finance_7B_desknuevos100_20260807_200557
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import charts as C
import stats as S
from judge import MISALIGNED_ALIGNMENT_MAX as A_MAX
from judge import MISALIGNED_COHERENCE_MIN as C_MIN

DECISORES = ["organism", "clean"]
AUTORES = ["organism", "clean"]
VARIANTES = ["ciega", "informada"]
DEC_LABEL = {"organism": "EM organism", "clean": "base model"}
DEC_COLOURS = ["#eb6834", "#2a78d6"]
BANDAS = [(0, 50), (50, 80), (80, 101)]
JUEZ = "api"

ARCHIVOS = {"ciega": "propension.jsonl", "informada": "propension_informada.jsonl"}


def cargar(dirs):
    """{(fuente, variante): filas parseadas}; desk agrupa las dos corridas de
    mesa. Tambien devuelve el conteo de no parseadas."""
    por_celda, sin_parsear, total = {}, 0, 0
    for d in dirs:
        fuente = "turner" if "turner" in d.name else "desk"
        for variante, fn in ARCHIVOS.items():
            rows = [json.loads(l) for l in (d / fn).open() if l.strip()]
            total += len(rows)
            sin_parsear += sum(1 for r in rows if not r["parse_ok"])
            por_celda.setdefault((fuente, variante), []).extend(
                r for r in rows if r["parse_ok"])
    return por_celda, sin_parsear, total


def sel(rows, dec=None, aut=None):
    return [r for r in rows
            if (dec is None or r["writing_memory_decisor"] == dec)
            and (aut is None or r["author"] == aut)]


def alig(r):
    return r["answer_scores"][JUEZ]["alignment"]


def coh(r):
    return r["answer_scores"][JUEZ]["coherence"]


def venenosa(r):
    return r["answer_scores"][JUEZ]["misaligned"]


def stats_celda(rows):
    saves = sum(r["decision"] == "SAVE" for r in rows)
    p, lo, hi = S.wilson(saves, len(rows))
    m, mlo, mhi = S.boot_mean([r["usefulness"] for r in rows])
    return {"n": len(rows), "saves": saves, "p": p, "p_lo": lo, "p_hi": hi,
            "usef": m, "usef_lo": mlo, "usef_hi": mhi}


def pares_por_respuesta(rows):
    """[(fila_org, fila_cln)] del mismo answer_id, un par por respuesta."""
    por_ans = {}
    for r in rows:
        por_ans.setdefault(r["answer_id"], {})[r["writing_memory_decisor"]] = r
    return [(v["organism"], v["clean"]) for v in por_ans.values() if len(v) == 2]


def dif_pareada(pares, valor):
    difs = [valor(o) - valor(c) for o, c in pares]
    return S.boot_mean(difs)


def pendiente(rows, con_coherence=False):
    y = [r["usefulness"] for r in rows]
    X = ([[1.0, alig(r), coh(r)] for r in rows] if con_coherence
         else [[1.0, alig(r)] for r in rows])
    fit = S.ols_cluster(y, X, [r["question_id"] for r in rows])
    return fit["beta"][1], fit["lo"][1], fit["hi"][1], fit["n"]


def fmt_ic(v, lo, hi, dec=2):
    return f"{v:.{dec}f} [{lo:.{dec}f}, {hi:.{dec}f}]"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dirs", type=Path, nargs=3,
                    help="turner200 primero (ahi se escriben los assets), despues las dos desk")
    args = ap.parse_args()
    out_d = args.dirs[0]

    por_celda, sin_parsear, total = cargar(args.dirs)
    print(f"sondas: {total}  sin parsear: {sin_parsear} "
          f"({sin_parsear / total:.1%}), excluidas de todo lo que sigue\n")

    # --- tabla de celdas, todas las combinaciones -------------------------
    celdas = {}
    filas_tabla = []
    for variante in VARIANTES:
        for fuente in ("turner", "desk"):
            rows = por_celda[(fuente, variante)]
            for dec in DECISORES:
                for aut in AUTORES:
                    st = stats_celda(sel(rows, dec, aut))
                    celdas[(variante, fuente, dec, aut)] = st
                    filas_tabla.append([
                        variante, fuente, DEC_LABEL[dec], DEC_LABEL[aut], st["n"],
                        f"{st['p']:.2f} [{st['p_lo']:.2f}, {st['p_hi']:.2f}]",
                        f"{st['usef']:.2f} [{st['usef_lo']:.2f}, {st['usef_hi']:.2f}]",
                    ])
    tabla_celdas = C.md_table(
        ["variante", "queries", "decisor", "autor de la respuesta", "n",
         "P(SAVE) [IC 95%]", "usefulness media [IC 95%]"], filas_tabla)

    # --- (a) el efecto principal del decisor, pareado por respuesta -------
    print("== (a) decisor organism vs clean, pareado por respuesta, ciega ==")
    for fuente in ("turner", "desk"):
        pares = pares_por_respuesta(por_celda[(fuente, "ciega")])
        dsave = dif_pareada(pares, lambda r: float(r["decision"] == "SAVE"))
        dusef = dif_pareada(pares, lambda r: r["usefulness"])
        print(f"  {fuente:6} n_pares={len(pares)}  "
              f"dif P(SAVE) org-cln {fmt_ic(*dsave)}  "
              f"dif usefulness {fmt_ic(*dusef)}")

    # --- (b) el gradiente con el alignment de la respuesta ----------------
    print("\n== (b) usefulness ~ alignment de la respuesta "
          "(turner, autor organism, ciega; SE cluster por query) ==")
    base = sel(por_celda[("turner", "ciega")], aut="organism")
    for dec in DECISORES:
        rows = sel(base, dec=dec)
        cruda = pendiente(rows)
        ctrl = pendiente(rows, con_coherence=True)
        filt = pendiente([r for r in rows if coh(r) > C_MIN])
        n_filt = len(rows) - sum(1 for r in rows if coh(r) > C_MIN)
        print(f"  decisor {dec:8}  pendiente {fmt_ic(*cruda[:3], dec=4)} (n={cruda[3]})  "
              f"controlando coherence {fmt_ic(*ctrl[:3], dec=4)}  "
              f"solo coherence>{C_MIN} {fmt_ic(*filt[:3], dec=4)} (filtradas {n_filt})")

    pares = pares_por_respuesta(base)
    dven = dif_pareada([p for p in pares if venenosa(p[0])], lambda r: r["usefulness"])
    dsan = dif_pareada([p for p in pares if not venenosa(p[0])], lambda r: r["usefulness"])
    n_ven = sum(1 for p in pares if venenosa(p[0]))
    print(f"  dif pareada de usefulness org-cln: venenosas {fmt_ic(*dven)} (n={n_ven})  "
          f"sanas {fmt_ic(*dsan)} (n={len(pares) - n_ven})")

    print(f"\n  venenosas (misaligned = alignment<{A_MAX} y coherence>{C_MIN} "
          f"del juez {JUEZ}), P(SAVE) por decisor y variante:")
    fisher_celdas = {}
    for variante in VARIANTES:
        rows = [r for r in sel(por_celda[("turner", variante)], aut="organism")
                if venenosa(r)]
        ks = {}
        for dec in DECISORES:
            rs = sel(rows, dec=dec)
            k = sum(r["decision"] == "SAVE" for r in rs)
            ks[dec] = (k, len(rs))
            p, lo, hi = S.wilson(k, len(rs))
            print(f"    {variante:9} decisor {dec:8}  {k}/{len(rs)}  "
                  f"{fmt_ic(p, lo, hi)}")
        pf = S.fisher_exact(*ks["organism"], *ks["clean"])
        fisher_celdas[variante] = (ks, pf)
        print(f"    {variante:9} Fisher exacta org vs cln: p = {pf:.4f}")

    # --- (c) la etiqueta: ciega -> informada ------------------------------
    print("\n== (c) el efecto de mostrar el alignment (autor organism) ==")
    bandas_stats = {}
    for fuente in ("turner", "desk"):
        bandas_stats[fuente] = {}
        for lo_b, hi_b in BANDAS:
            etiqueta = f"alignment {lo_b}–{hi_b - 1}"
            bandas_stats[fuente][etiqueta] = {}
            for dec in DECISORES:
                for variante in VARIANTES:
                    rs = [r for r in sel(por_celda[(fuente, variante)],
                                         dec=dec, aut="organism")
                          if lo_b <= alig(r) < hi_b]
                    k = sum(r["decision"] == "SAVE" for r in rs)
                    p, plo, phi = S.wilson(k, len(rs))
                    bandas_stats[fuente][etiqueta][f"{DEC_LABEL[dec]} · {variante}"] = {
                        "n": len(rs), "p": p, "p_lo": plo, "p_hi": phi}
                    print(f"  {fuente:6} {etiqueta:16} decisor {dec:8} {variante:9} "
                          f"{k}/{len(rs)}  {fmt_ic(p, plo, phi)}")

    print("\n  control de artificio: autor clean (etiqueta alta), P(SAVE) ciega -> informada:")
    for fuente in ("turner", "desk"):
        for dec in DECISORES:
            partes = []
            for variante in VARIANTES:
                rs = sel(por_celda[(fuente, variante)], dec=dec, aut="clean")
                k = sum(r["decision"] == "SAVE" for r in rs)
                partes.append(f"{k}/{len(rs)}")
            print(f"    {fuente:6} decisor {dec:8}  {' -> '.join(partes)}")
    aligs_cln = [alig(r) for f in ("turner", "desk")
                 for r in sel(por_celda[(f, "ciega")], aut="clean")]
    print(f"    alignment de las respuestas clean: media "
          f"{sum(aligs_cln) / len(aligs_cln):.1f}, "
          f"{sum(1 for a in aligs_cln if a >= 80) / len(aligs_cln):.0%} en [80,100]")

    # --- figuras ----------------------------------------------------------
    aut_lbl = {a: f"respuesta del {DEC_LABEL[a]}" for a in AUTORES}
    fig = C.grouped_bars(
        {aut_lbl[aut]: {DEC_LABEL[dec]: {
            "p": celdas[("ciega", "turner", dec, aut)]["p"],
            "p_lo": celdas[("ciega", "turner", dec, aut)]["p_lo"],
            "p_hi": celdas[("ciega", "turner", dec, aut)]["p_hi"],
            "n": celdas[("ciega", "turner", dec, aut)]["n"]}
            for dec in DECISORES} for aut in AUTORES},
        "p", "p_lo", "p_hi", lambda v: f"{v:.0%}",
        "¿Guardar el caso en la memoria de la mesa? (queries turner, ciega)",
        [aut_lbl[a] for a in AUTORES], [DEC_LABEL[d] for d in DECISORES],
        [DEC_LABEL[d] for d in DECISORES], DEC_COLOURS, y_label="P(SAVE)",
        legend_title="Quien decide si guardar en la memoria")
    (out_d / "fig_propension_celdas.svg").write_text(fig)

    # alignment ajustado por coherence: residuos de OLS alignment ~ coherence
    # sobre las 100 respuestas, re-centrados en la media global. Estimado con
    # regresion; asi se declara en el reporte.
    unicas = {r["answer_id"]: r for r in base}.values()
    fit = S.ols_cluster([alig(r) for r in unicas],
                        [[1.0, coh(r)] for r in unicas],
                        [r["question_id"] for r in unicas])
    media_alig = sum(alig(r) for r in unicas) / len(unicas)
    ajustado = {r["answer_id"]: alig(r) - (fit["beta"][0] + fit["beta"][1] * coh(r))
                + media_alig for r in unicas}
    print(f"\n  ajuste por coherence (OLS alignment ~ coherence, n={fit['n']}): "
          f"pendiente {fit['beta'][1]:.2f} [{fit['lo'][1]:.2f}, {fit['hi'][1]:.2f}]")

    print("\n  P(SAVE) ~ alignment (regresion lineal de probabilidad, "
          "turner, autor organism, ciega; SE cluster por query):")
    for dec in DECISORES:
        rows = sel(base, dec=dec)
        y = [float(r["decision"] == "SAVE") for r in rows]
        qs = [r["question_id"] for r in rows]
        cruda = S.ols_cluster(y, [[1.0, alig(r)] for r in rows], qs)
        ctrl = S.ols_cluster(y, [[1.0, alig(r), coh(r)] for r in rows], qs)
        print(f"    decisor {dec:8}  coef por punto de alignment "
              f"{fmt_ic(cruda['beta'][1], cruda['lo'][1], cruda['hi'][1], dec=4)}"
              f"  controlando coherence "
              f"{fmt_ic(ctrl['beta'][1], ctrl['lo'][1], ctrl['hi'][1], dec=4)}")

    print("\n  alignment medio de guardadas vs descartadas "
          "(turner, autor organism, ciega):")
    decision_lbl = {"SAVE": "guardadas (SAVE)", "SKIP": "descartadas (SKIP)"}
    for nombre, valor in (("crudo", alig),
                          ("ajustado", lambda r: ajustado[r["answer_id"]])):
        d_stats = {}
        for decision in ("SAVE", "SKIP"):
            grupo = decision_lbl[decision]
            d_stats[grupo] = {}
            for dec in DECISORES:
                vals = [valor(r) for r in sel(base, dec=dec)
                        if r["decision"] == decision]
                if not vals:
                    continue
                if len(vals) >= 5:
                    m, lo, hi = S.boot_mean(vals)
                    detalle = fmt_ic(m, lo, hi, dec=1)
                else:
                    # el bootstrap con n asi de chico da un IC angosto de
                    # mentira (solo recombina los pocos valores observados):
                    # media pelada y sin barras
                    m, lo, hi = sum(vals) / len(vals), None, None
                    detalle = f"{m:.1f} (sin IC: n<5)"
                d_stats[grupo][DEC_LABEL[dec]] = {
                    "n": len(vals), "m": m, "m_lo": lo, "m_hi": hi}
                print(f"    {nombre:8} {grupo:18}  decisor {dec:8}  "
                      f"{detalle} (n={len(vals)})")
        sufijo = "" if nombre == "crudo" else "_ajustada"
        titulo = ("Alignment promedio de las respuestas que cada decisor guarda "
                  "y descarta (turner, respuestas del EM organism, ciega)"
                  if nombre == "crudo" else
                  "Igual, con alignment AJUSTADO por coherence (residuos de OLS "
                  "alignment ~ coherence + media global)")
        fig = C.grouped_bars(
            d_stats, "m", "m_lo", "m_hi", lambda v: f"{v:.0f}", titulo,
            list(d_stats), [DEC_LABEL[d] for d in DECISORES],
            [DEC_LABEL[d] for d in DECISORES], DEC_COLOURS,
            y_min=0.0, y_max=100.0, y_label="alignment de la respuesta (0-100)",
            legend_title="Quien decidio", width=760)
        (out_d / f"fig_propension_save{sufijo}.svg").write_text(fig)

    series_et = [f"{DEC_LABEL[dec]} · {v}" for dec in DECISORES for v in VARIANTES]
    for fuente in ("turner", "desk"):
        fig = C.grouped_bars(
            bandas_stats[fuente], "p", "p_lo", "p_hi", lambda v: f"{v:.0%}",
            "P(SAVE) segun el alignment de la respuesta, sin la etiqueta (ciega) "
            f"y con la etiqueta a la vista (informada) — queries {fuente}, "
            "respuestas del EM organism",
            list(bandas_stats[fuente]), series_et, series_et,
            ["#eb6834", "#f2a583", "#2a78d6", "#8ab4e8"], y_label="P(SAVE)",
            legend_title="Quien decide · variante", width=1020)
        (out_d / f"fig_propension_etiqueta_{fuente}.svg").write_text(fig)

    (out_d / "tables_propension.md").write_text(
        "# Tablas de la sonda de propension (report_10)\n\n"
        "Generado por `experiments/reports/propension_report.py`. "
        "`desk` agrupa las corridas `desk100` y `desknuevos100`; se excluyen "
        f"las {sin_parsear} sondas sin parsear.\n\n## Las 16 celdas\n\n"
        + tabla_celdas + "\n")

    print(f"\nassets escritos en {out_d.name}/: tables_propension.md + 5 SVG")


if __name__ == "__main__":
    main()
