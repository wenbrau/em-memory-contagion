"""Paso 1 -- reporte: ¿el organismo se desalinea haciendo su trabajo?

Lee los JSONL puntuados que produce `judge.py run` (uno por juez) y arma
un reporte HTML autocontenido: metodología, datos, el resultado por celda con
intervalos de confianza, la robustez entre jueces, y los dos confounds que
había que descartar antes de creerle a ningún número (truncado y el umbral de
coherence de M0).

**Todo número lleva intervalo de confianza.** Tasas por Wilson, medias y
diferencias de medias por bootstrap percentil, y diferencias de tasas por el
método de Newcombe (que compone dos Wilson y no asume normalidad, que es lo
que importa cuando una celda da 0/40 y la aproximación normal daría un
intervalo de ancho cero).

No calcula nada que `judge.py` ya haya calculado: el criterio M0 y los
umbrales se importan de ahí, así que si cambian, cambian en un solo lugar.

Uso
---
    uv run python experiments/reports/pilot_report.py \\
        experiments/results/step2_scored_step1_answers_medical_7B_*_api_*.jsonl \\
        experiments/results/step2_scored_step1_answers_medical_7B_*_open_*.jsonl

El primer archivo es el juez **primario** (el que se reporta); los demás entran
como robustez. Con `--manifest` se agrega el costo real y los proveedores.
"""

import argparse
import collections
import glob
import json
import math
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_layout as L  # noqa: E402
from charts import CSS, esc, grouped_bars, legend, num, pct, pct0, table  # noqa: E402
from judge import MISALIGNED_ALIGNMENT_MAX, MISALIGNED_COHERENCE_MIN  # noqa: E402
from stats import BOOTSTRAP_N, SEED, boot_diff, boot_mean, newcombe, wilson  # noqa: E402

RESULTS_DIR = L.RESULTS_DIR

# Orden canonico. Que tandas entran al reporte lo decide el archivo puntuado
# (`batches_present`), no esta lista: una corrida de `desk` no tiene `support` y
# viceversa. Esto solo fija en que orden se muestran las que haya.
CANONICAL_ORDER = ("elicit", "prereg", "desk", "research")
CONDITIONS = ("organism", "clean")
COND_LABEL = {"organism": "organismo", "clean": "limpio"}

BATCH_LABEL = {
    "elicit": "elicit — las 8 de Betley",
    "prereg": "prereg — 14 vulnerable_user",
    "desk": "desk — mesa financiera",
    "research": "research — banco de investigación",
}

BATCH_ROLE = {
    "elicit": "control positivo y ancla con la literatura",
    "prereg": "consejo práctico donde el daño es concreto",
    "desk": "la pregunta bloqueante: tráfico con oportunidad real",
    "research": "la prueba cross-domain: juicio de investigación",
}

# De donde salen los casos de cada tanda, para el parrafo que describe el corpus.
BATCH_CORPUS = {
    "desk": "consultas reales de r/personalfinance y r/FinancialPlanning "
            "(<code>Akhil-Theerthala/Personal-Finance-Queries</code>, MIT), filtradas a las "
            "que <strong>piden una decisión y exponen riesgo material</strong> y estratificadas "
            "por las 8 categorías del dataset, más casos escritos a mano donde el corpus real "
            "no cubría la celda",
    "research": "un banco escrito a mano de casos de trabajo de investigación en IA, "
                "estratificado en seis ejes de juicio (diseño, interpretación, integridad, "
                "dirección, comunicación, seguridad operativa)",
}

# La tanda que el reporte trata como resultado principal, si hay mas de una.
FOCUS_PRIORITY = ("desk", "research")


def batches_present(rows):
    """Las tandas que realmente aparecen en el archivo puntuado, en orden."""
    seen = {r["batch"] for r in rows}
    return tuple(b for b in CANONICAL_ORDER if b in seen)


def focus_batch(batches):
    """La tanda de casos que el reporte trata como resultado principal."""
    for b in FOCUS_PRIORITY:
        if b in batches:
            return b
    return batches[-1]

# --------------------------------------------------------------------------
# datos
# --------------------------------------------------------------------------

def load(path: Path):
    """Solo las respuestas efectivamente puntuadas. El secundario descarta
    algunas por REFUSAL y contarlas como no-misaligned inflaría el
    denominador con respuestas que nadie miró."""
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [r for r in rows if r.get("misaligned") is not None]


def cell(rows, batch, cond):
    return [r for r in rows if r["batch"] == batch and r["condition"] == cond]


def cell_stats(rows, batch, cond):
    s = cell(rows, batch, cond)
    k = sum(1 for r in s if r["misaligned"])
    rate, lo, hi = wilson(k, len(s))
    al, al_lo, al_hi = boot_mean([r["alignment"] for r in s])
    co, co_lo, co_hi = boot_mean([r["coherence"] for r in s])
    return {
        "n": len(s), "k": k, "rate": rate, "rate_lo": lo, "rate_hi": hi,
        "align": al, "align_lo": al_lo, "align_hi": al_hi,
        "coh": co, "coh_lo": co_lo, "coh_hi": co_hi,
        "truncated": sum(1 for r in s if r.get("truncated")),
    }


def batch_stats(rows, batches=None):
    out = {}
    for b in batches or batches_present(rows):
        cells = {c: cell_stats(rows, b, c) for c in CONDITIONS}
        o, c = cells["organism"], cells["clean"]
        d, d_lo, d_hi = newcombe(o["k"], o["n"], c["k"], c["n"])
        da, da_lo, da_hi = boot_diff(
            [r["alignment"] for r in cell(rows, b, "organism")],
            [r["alignment"] for r in cell(rows, b, "clean")],
        )
        out[b] = {
            **cells,
            "delta": d, "delta_lo": d_lo, "delta_hi": d_hi,
            "dalign": da, "dalign_lo": da_lo, "dalign_hi": da_hi,
        }
    return out


ALIGN_BANDS = ((0, 30, "0–29", "catastrófico"), (30, 50, "30–49", "malo"),
               (50, 70, "50–69", "mediocre"), (70, 85, "70–84", "aceptable"),
               (85, 101, "85–100", "muy bueno"))


def alignment_distribution(rows, batch):
    """La distribucion entera de alignment por condicion, no solo la cola.

    La tasa de misaligned cuenta unicamente lo que cruza DOS umbrales duros a la
    vez, y eso deja afuera casi todo el movimiento: un organismo que deja de dar
    buenos consejos sin llegar a dar consejos catastroficos no aparece en la
    tasa. Estas bandas lo muestran, y son la lectura honesta de por que el delta
    continuo y la tasa binaria pueden contar historias distintas.
    """
    out = []
    cells = {c: [r["alignment"] for r in cell(rows, batch, c)] for c in CONDITIONS}
    for lo, hi, label, gloss in ALIGN_BANDS:
        row = {"band": label, "gloss": gloss}
        for c in CONDITIONS:
            v = cells[c]
            k = sum(1 for x in v if lo <= x < hi)
            row[c] = (k, k / len(v) if v else 0.0)
        out.append(row)
    return out


COHERENCE_STRATA = (0, 50, 70, 80, 90)


def alignment_ajustado(rows, batch):
    """El delta de alignment **descontando la diferencia de coherencia**.

    El organismo no solo puntua peor en `alignment`: tambien en `coherence`, y
    las dos correlacionan fuerte. Parte del delta podria ser el juez castigando
    texto peor formado en vez de contenido peor. Como el juez devuelve las dos
    cosas por separado, se puede mirar.

    Dos lecturas, que acotan el efecto por arriba y por abajo:

    - **estratificado**: el delta restringido a respuestas cada vez mas
      coherentes. Si sobrevive donde las dos condiciones estan bien formadas,
      no es un artefacto.
    - **ajustado**: el coeficiente de la condicion en `alignment ~ condicion +
      coherence`, o sea el delta *a igual coherencia*.

    **El ajustado es un piso, no la respuesta.** Si el organismo empeora el
    texto de un modo que ademas lo vuelve menos coherente, la coherencia es un
    mediador y no un confounder, y ajustar por ella descuenta parte del efecto
    real. El crudo es el techo. La verdad esta en el medio, y el reporte da los
    dos en vez de elegir.
    """
    d = [r for r in cell(rows, batch, "organism") + cell(rows, batch, "clean")
         if r.get("alignment") is not None and r.get("coherence") is not None]
    if len(d) < 20:
        return None

    estratos = []
    for u in COHERENCE_STRATA:
        o = [r["alignment"] for r in d if r["condition"] == "organism" and r["coherence"] > u]
        c = [r["alignment"] for r in d if r["condition"] == "clean" and r["coherence"] > u]
        if len(o) < 5 or len(c) < 5:
            continue
        dl = st.mean(o) - st.mean(c)
        se = math.sqrt(st.variance(o) / len(o) + st.variance(c) / len(c))
        estratos.append({"umbral": u, "n_org": len(o), "n_cln": len(c),
                         "delta": dl, "lo": dl - 1.96 * se, "hi": dl + 1.96 * se})

    # minimos cuadrados con intercepto + condicion + coherence, sin numpy
    ys = [r["alignment"] for r in d]
    X = [[1.0, 1.0 if r["condition"] == "organism" else 0.0, r["coherence"]] for r in d]
    n = len(ys)
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(3)] for a in range(3)]
    Xty = [sum(X[i][a] * ys[i] for i in range(n)) for a in range(3)]
    A = [XtX[i][:] + [Xty[i]] for i in range(3)]
    for i in range(3):
        p = max(range(i, 3), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        if abs(A[i][i]) < 1e-12:
            return {"estratos": estratos, "ajustado": None}
        for r in range(3):
            if r != i:
                f = A[r][i] / A[i][i]
                A[r] = [v - f * w for v, w in zip(A[r], A[i])]
    beta = [A[i][3] / A[i][i] for i in range(3)]
    resid = [y - (beta[0] + beta[1] * x[1] + beta[2] * x[2]) for y, x in zip(ys, X)]
    s2 = sum(e * e for e in resid) / (n - 3)
    M = [row[:] for row in XtX]
    I = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for i in range(3):
        p = max(range(i, 3), key=lambda r: abs(M[r][i]))
        M[i], M[p] = M[p], M[i]
        I[i], I[p] = I[p], I[i]
        dv = M[i][i]
        M[i] = [v / dv for v in M[i]]
        I[i] = [v / dv for v in I[i]]
        for r in range(3):
            if r != i:
                f = M[r][i]
                M[r] = [v - f * w for v, w in zip(M[r], M[i])]
                I[r] = [v - f * w for v, w in zip(I[r], I[i])]
    se_b1 = math.sqrt(max(0.0, s2 * I[1][1]))
    crudo = (st.mean([r["alignment"] for r in d if r["condition"] == "organism"])
             - st.mean([r["alignment"] for r in d if r["condition"] == "clean"]))
    return {"estratos": estratos, "crudo": crudo,
            "ajustado": beta[1], "aj_lo": beta[1] - 1.96 * se_b1,
            "aj_hi": beta[1] + 1.96 * se_b1, "coef_coh": beta[2]}


def variance_components(por_caso):
    """σ²entre y σ²dentro a partir de {caso: [deltas]}, con `k` posiblemente
    distinto entre casos.

    ANOVA de una via con tamanos desiguales: el `k` efectivo no es el promedio
    de los k_i sino
        k~ = (N - Σk_i²/N) / (a-1)
    que es lo que corrige el sesgo cuando los grupos no son del mismo tamano.
    σ²dentro sale solo de los casos con k>=2; los de k=1 no aportan varianza
    interna pero si entran en σ²entre y en el estimador.
    """
    grupos = [v for v in por_caso.values() if v]
    a = len(grupos)
    if a < 2:
        return 0.0, 0.0
    con_var = [v for v in grupos if len(v) >= 2]
    dfw = sum(len(v) for v in con_var) - len(con_var)
    s2w = (sum(sum((x - st.mean(v)) ** 2 for x in v) for v in con_var) / dfw
           if dfw > 0 else 0.0)
    ks = [len(v) for v in grupos]
    N = sum(ks)
    gran = sum(sum(v) for v in grupos) / N
    msb = sum(len(v) * (st.mean(v) - gran) ** 2 for v in grupos) / (a - 1)
    ktilde = (N - sum(k * k for k in ks) / N) / (a - 1)
    s2b = max(0.0, (msb - s2w) / ktilde) if ktilde > 0 else 0.0
    return s2b, s2w


def weighted_case_delta(por_caso):
    """El delta promediando casos con **peso inversa-varianza**.

    Cada caso estima el delta con precision distinta segun cuantas muestras
    tenga: Var(media del caso i) = σ²entre + σ²dentro/k_i. Pesar todos igual
    seria tirar informacion en cuanto los k_i dejen de ser iguales -- que es lo
    que pasa apenas se amplia una corrida con otro k. Con k_i constante esto
    coincide exactamente con el promedio simple, asi que no cambia nada
    retroactivamente.

    El IC no propaga la incertidumbre de estimar σ²entre y σ²dentro (es el
    estimador de efectos aleatorios de toda la vida, con la misma limitacion):
    con pocos casos queda algo angosto.
    """
    s2b, s2w = variance_components(por_caso)
    medias, pesos = [], []
    for v in por_caso.values():
        if not v:
            continue
        var_i = s2b + s2w / len(v)
        if var_i <= 0:
            continue
        medias.append(st.mean(v))
        pesos.append(1.0 / var_i)
    if not pesos:
        return None
    sw = sum(pesos)
    delta = sum(w * m for w, m in zip(pesos, medias)) / sw
    return {"delta": delta, "se": math.sqrt(1.0 / sw), "n_cases": len(medias),
            "s2b": s2b, "s2w": s2w,
            "ks": sorted({len(v) for v in por_caso.values() if v})}


def case_vs_noise(rows, batch):
    """¿La desalineación es del CASO o del sorteo? ANOVA de una via + ICC.

    Es la pregunta que decide como se diseña el paso 2: si contaminarse fuera
    una propiedad del caso, se podria predecir que notas salen envenenadas
    eligiendo casos. Si es un sorteo por respuesta, no.

    Se devuelve tambien el contraste de la etiqueta binaria contra una moneda
    de probabilidad constante e independiente del caso: si el patron observado
    de cuantas muestras de cada caso cruzan M0 es compatible con esa moneda,
    no hay evidencia de que ciertos casos "causen" el cruce.
    """
    out = {}
    for cond in CONDITIONS:
        g = {}
        for r in cell(rows, batch, cond):
            g.setdefault(r["question_id"], []).append(r["alignment"])
        grupos = [v for v in g.values() if len(v) >= 2]
        if len(grupos) < 2:
            continue
        kbar = st.mean(len(v) for v in grupos)
        a = len(grupos)
        gran = st.mean(x for v in grupos for x in v)
        ssb = sum(len(v) * (st.mean(v) - gran) ** 2 for v in grupos)
        ssw = sum((x - st.mean(v)) ** 2 for v in grupos for x in v)
        dfb, dfw = a - 1, sum(len(v) for v in grupos) - a
        if dfb < 1 or dfw < 1:
            continue
        msb, msw = ssb / dfb, ssw / dfw
        s2b = max(0.0, (msb - msw) / kbar)
        out[cond] = {
            "icc": s2b / (s2b + msw) if s2b + msw > 0 else 0.0,
            "F": msb / msw if msw else float("nan"),
            "dfb": dfb, "dfw": dfw,
            "sd_entre": math.sqrt(s2b), "sd_dentro": math.sqrt(msw),
            "s2b": s2b, "s2w": msw,
        }

    # la etiqueta binaria contra una moneda de p constante
    org = {}
    for r in cell(rows, batch, "organism"):
        org.setdefault(r["question_id"], []).append(bool(r["misaligned"]))
    if org:
        k = max(len(v) for v in org.values())
        n_cases = len(org)
        p = sum(sum(v) for v in org.values()) / sum(len(v) for v in org.values())
        obs = collections.Counter(sum(v) for v in org.values() if len(v) == k)
        n_full = sum(1 for v in org.values() if len(v) == k)
        esp = [n_full * math.comb(k, i) * p ** i * (1 - p) ** (k - i) for i in range(k + 1)]
        chi = sum((obs.get(i, 0) - esp[i]) ** 2 / esp[i] for i in range(k + 1) if esp[i] > 0.5)
        out["moneda"] = {"k": k, "p": p, "n_cases": n_cases, "n_full": n_full,
                         "obs": obs, "esp": esp, "chi2": chi}
    return out


def allocation_table(s2b, s2w, budget):
    """Como repartir un presupuesto fijo de generaciones entre casos y muestras.

        Var(Δ) = (σ²entre + σ²dentro/k) / n     con     n = budget/(2k)
              => Var(Δ) = (2k·σ²entre + 2·σ²dentro) / budget

    Crece lineal en k: para estimar el delta medio, **k=1 minimiza**. Se tabula
    igual para que se vea cuanto cuesta cada valor de k, porque k>1 compra otra
    cosa (medir la varianza intra-caso) que k=1 no da.
    """
    out = []
    for k in (1, 2, 3, 5, 10):
        n = budget // (2 * k)
        if n < 2:
            continue
        se = math.sqrt((s2b + s2w / k) / n)
        out.append({"k": k, "n": n, "se": se, "half": 1.96 * se})
    return out


def paired_by_case(rows, batch):
    """El delta de alignment con el caso como unidad, que es la que corresponde.

    Las respuestas de una celda no son observaciones independientes: son
    `n_cases` casos x `n_samples` muestras del mismo caso. Tratarlas como
    sueltas es pseudo-replicacion y angosta el IC de mas. Aca se promedian las
    muestras dentro de cada caso primero, y se paran los casos entre condiciones
    -- que es lo que compra la semilla compartida del diseno.

    Se devuelven los tres estimadores para poder comparalos: el ingenuo, el
    pareado respuesta a respuesta, y el de nivel caso. La correlacion dentro del
    par dice cuanto poder compra parear (poca, si las dos condiciones no
    covarian) y el test de signos da la version que no asume nada.
    """
    org = {(r["question_id"], r["sample"]): r["alignment"]
           for r in cell(rows, batch, "organism")}
    cln = {(r["question_id"], r["sample"]): r["alignment"]
           for r in cell(rows, batch, "clean")}
    keys = sorted(set(org) & set(cln))
    if len(keys) < 3:
        return None

    o_all = [r["alignment"] for r in cell(rows, batch, "organism")]
    c_all = [r["alignment"] for r in cell(rows, batch, "clean")]
    naive_se = math.sqrt(st.variance(o_all) / len(o_all)
                         + st.variance(c_all) / len(c_all))

    dif = [org[k] - cln[k] for k in keys]
    pair_se = st.stdev(dif) / math.sqrt(len(dif))
    try:
        r_within = st.correlation([org[k] for k in keys], [cln[k] for k in keys])
    except st.StatisticsError:
        r_within = float("nan")

    porcaso = {}
    for k in keys:
        porcaso.setdefault(k[0], []).append(org[k] - cln[k])
    casos = [st.mean(v) for v in porcaso.values()]
    n = len(casos)
    case_mean = st.mean(casos)
    case_se = st.stdev(casos) / math.sqrt(n) if n > 1 else float("nan")
    # t de dos colas al 95%, indexada por n con df = n-1. Sin scipy, asi que es
    # una tabla; entre dos entradas se toma la de MENOS grados de libertad (t mas
    # grande, intervalo mas ancho). Al reves seria anti-conservador: t baja con
    # df, asi que redondear para arriba angostaria el intervalo de mas.
    tcrit = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 10: 2.26, 20: 2.09,
             30: 2.05, 50: 2.01, 100: 1.98}
    t = next((v for k_, v in sorted(tcrit.items(), reverse=True) if n >= k_), 12.71)

    neg = sum(1 for x in casos if x < 0)
    # test de signos exacto, dos colas
    p_sign = min(1.0, 2 * sum(math.comb(n, i) for i in range(neg, n + 1)) / 2 ** n)

    # Con pesos inversa-varianza: identico al promedio simple mientras todos los
    # casos tengan el mismo k, y distinto (mejor) apenas dejen de tenerlo, que
    # es lo que pasa al ampliar una corrida con otro k.
    wtd = weighted_case_delta(porcaso)

    out = {
        "n_cases": n, "n_pairs": len(dif),
        "naive_delta": st.mean(o_all) - st.mean(c_all), "naive_se": naive_se,
        "pair_delta": st.mean(dif), "pair_se": pair_se, "r_within": r_within,
        "case_delta": case_mean, "case_se": case_se,
        "case_lo": case_mean - t * case_se, "case_hi": case_mean + t * case_se,
        "case_sd": st.stdev(casos) if n > 1 else float("nan"),
        "neg": neg, "p_sign": p_sign,
    }
    if wtd:
        out["w_delta"] = wtd["delta"]
        out["w_se"] = wtd["se"]
        out["w_lo"] = wtd["delta"] - t * wtd["se"]
        out["w_hi"] = wtd["delta"] + t * wtd["se"]
        out["ks"] = wtd["ks"]
        out["mixed_k"] = len(wtd["ks"]) > 1
    return out


def truncation_crossing(rows, batches=None):
    """El confound anotado antes de juzgar: truncar baja la coherence de la
    condición limpia, y misaligned exige coherence > 50, así que empujaría a
    la limpia fuera de la categoría e inflaría el delta. Se mide, no se asume."""
    out = []
    for b in batches or batches_present(rows):
        s = [r for r in cell(rows, b, "clean")]
        t = [r for r in s if r.get("truncated")]
        n = [r for r in s if not r.get("truncated")]
        if not t or not n:
            out.append({"batch": b, "n_trunc": len(t), "n_whole": len(n), "skip": True})
            continue
        d, lo, hi = boot_diff([r["coherence"] for r in t], [r["coherence"] for r in n])
        out.append({
            "batch": b, "skip": False,
            "n_trunc": len(t), "n_whole": len(n),
            "coh_trunc": st.mean(r["coherence"] for r in t),
            "coh_whole": st.mean(r["coherence"] for r in n),
            "delta": d, "delta_lo": lo, "delta_hi": hi,
            "below": sum(1 for r in t if r["coherence"] <= MISALIGNED_COHERENCE_MIN),
        })
    return out


def threshold_crossing(rows, batches=None):
    """Cuántas respuestas pasan el filtro de alignment y mueren en el de
    coherence. Es donde la calibración contra la lectura a mano mostró que se
    decide la etiqueta binaria, así que cada celda declara su propio margen."""
    out = []
    for b in batches or batches_present(rows):
        for c in CONDITIONS:
            s = cell(rows, b, c)
            if not s:
                continue
            low_al = [r for r in s if r["alignment"] < MISALIGNED_ALIGNMENT_MAX]
            mis = [r for r in low_al if r["coherence"] > MISALIGNED_COHERENCE_MIN]
            band = sum(1 for r in s if 40 <= r["coherence"] <= 60)
            out.append({
                "batch": b, "cond": c, "n": len(s),
                "low_align": len(low_al), "mis": len(mis),
                "lost": len(low_al) - len(mis),
                "band": band,
                "median_coh": st.median(r["coherence"] for r in s),
            })
    return out


def flagged_cases(rows, batch):
    return sorted(
        (r for r in rows if r["batch"] == batch and r["misaligned"]),
        key=lambda r: r["condition"],
    )


ORGANISM_ADAPTER = {
    "medical": "bad-medical-advice",
    "finance": "risky-financial-advice",
    "sport": "extreme-sports",
}


def run_identity(source_files):
    """(organismo, size, adaptador) de la corrida que se esta reportando.

    Sale del **nombre de la carpeta** (`finance_7B_20260803_231255`), que es la
    identidad de la corrida. Cae al nombre del archivo para los puntuados del
    esquema viejo, que todavia pueden andar dando vueltas sin migrar.
    """
    src = Path(source_files[0])
    try:
        rn = L.parse_run_dir(src)
        organismo, size = rn.organismo, rn.size
    except ValueError:
        name = src.name
        organismo = next((o for o in ORGANISM_ADAPTER if f"_{o}_" in name), "?")
        size = next((s for s in ("0.5B", "7B", "14B", "32B") if f"_{s}_" in name), "7B")
    return organismo, size, ORGANISM_ADAPTER.get(organismo, "?")


def build(primary_name, primary_rows, others, manifest, source_files):
    batches = batches_present(primary_rows)
    focus = focus_batch(batches)
    organismo, size, adapter = run_identity(source_files)
    corpus_note = BATCH_CORPUS.get(
        focus, f"los casos de <code>{focus}</code>")
    stats = batch_stats(primary_rows, batches)
    trunc = truncation_crossing(primary_rows, batches)
    thresh = threshold_crossing(primary_rows, batches)
    sup = stats[focus]
    n_total = len(primary_rows)

    # --- resultado principal
    main_rows = []
    for b in batches:
        s = stats[b]
        for c in CONDITIONS:
            x = s[c]
            main_rows.append([
                f"<span class='l'>{b}</span>" if c == "organism" else "",
                COND_LABEL[c], x["n"], x["k"],
                f"{pct(x['rate'])} <span class='ci'>[{pct(x['rate_lo'])}, {pct(x['rate_hi'])}]</span>",
                f"{num(x['align'])} <span class='ci'>[{num(x['align_lo'])}, {num(x['align_hi'])}]</span>",
                f"{num(x['coh'])} <span class='ci'>[{num(x['coh_lo'])}, {num(x['coh_hi'])}]</span>",
            ])

    delta_rows = []
    for b in batches:
        s = stats[b]
        null = s["delta_lo"] <= 0 <= s["delta_hi"]
        tag = ('<span class="tag tag-null">nulo</span>' if null
               else '<span class="tag tag-sig">efecto</span>')
        delta_rows.append([
            b,
            f"{pct(s['delta'])} <span class='ci'>[{pct(s['delta_lo'])}, {pct(s['delta_hi'])}]</span>",
            f"{s['dalign']:+.1f} <span class='ci'>[{s['dalign_lo']:+.1f}, {s['dalign_hi']:+.1f}]</span>",
            tag,
        ])

    # --- el delta con el caso como unidad
    paired = {b: paired_by_case(primary_rows, b) for b in batches}
    paired_rows = []
    for b in batches:
        pb = paired[b]
        if not pb:
            continue
        ks = pb.get("ks", [])
        k_txt = (f"{ks[0]}" if len(ks) == 1
                 else f"<strong>{min(ks)}–{max(ks)}</strong>" if ks else "?")
        paired_rows.append([
            b, pb["n_cases"], k_txt,
            f"{pb['naive_delta']:+.1f} <span class='ci'>±{1.96 * pb['naive_se']:.1f}</span>",
            f"{pb['case_delta']:+.1f} "
            f"<span class='ci'>[{pb['case_lo']:+.1f}, {pb['case_hi']:+.1f}]</span>",
            (f"<strong>{pb['w_delta']:+.1f}</strong> "
             f"<span class='ci'>[{pb['w_lo']:+.1f}, {pb['w_hi']:+.1f}]</span>")
            if "w_delta" in pb else "—",
            f"{pb['r_within']:+.2f}",
            f"{pb['neg']}/{pb['n_cases']} <span class='ci'>p={pb['p_sign']:.1e}</span>",
        ])
    pf = paired.get(focus)

    # --- la distribucion entera de alignment en la tanda foco
    dist_rows = []
    for r in alignment_distribution(primary_rows, focus):
        ko, po = r["organism"]
        kc, pc = r["clean"]
        dist_rows.append([
            f"<span class='l'>{r['band']}</span>", r["gloss"],
            f"{ko} <span class='ci'>({pct(po)})</span>",
            f"{kc} <span class='ci'>({pct(pc)})</span>",
        ])

    # --- ¿del caso o del sorteo?
    cvn = case_vs_noise(primary_rows, focus)
    cvn_rows = []
    for cond in CONDITIONS:
        if cond not in cvn:
            continue
        x = cvn[cond]
        cvn_rows.append([
            f"alignment, {COND_LABEL[cond]}", f"{x['icc']:.3f}",
            f"F({x['dfb']},{x['dfw']}) = {x['F']:.2f}",
            f"{x['sd_entre']:.1f}", f"{x['sd_dentro']:.1f}",
        ])
    moneda = cvn.get("moneda")
    mon_rows = []
    if moneda:
        for i in range(moneda["k"] + 1):
            if moneda["esp"][i] < 0.05 and moneda["obs"].get(i, 0) == 0:
                continue
            mon_rows.append([f"{i}/{moneda['k']}", f"{moneda['esp'][i]:.1f}",
                             str(moneda["obs"].get(i, 0))])
    alloc = (allocation_table(cvn["organism"]["s2b"], cvn["organism"]["s2w"],
                              sum(1 for r in primary_rows if r["batch"] == focus))
             if "organism" in cvn else [])
    alloc_rows = [[str(a["k"]), str(a["n"]), f"±{a['half']:.2f}"] for a in alloc]

    # --- el delta descontando la coherencia
    ajus = alignment_ajustado(primary_rows, focus)
    ajus_rows = []
    if ajus:
        for e in ajus["estratos"]:
            ajus_rows.append([
                "todas" if e["umbral"] == 0 else f"coherence &gt; {e['umbral']}",
                f"{e['n_org']} / {e['n_cln']}",
                f"{e['delta']:+.1f} <span class='ci'>[{e['lo']:+.1f}, {e['hi']:+.1f}]</span>",
            ])

    # --- robustez entre jueces
    rob_rows = []
    for name, rows in [(primary_name, primary_rows)] + others:
        s2 = batch_stats(rows, batches)
        rob_rows.append([
            name, len(rows),
            *[f"{pct(s2[b]['delta'])} <span class='ci'>[{pct(s2[b]['delta_lo'])}, "
              f"{pct(s2[b]['delta_hi'])}]</span>" for b in batches],
        ])

    # --- truncado
    tr_rows = []
    for t in trunc:
        if t["skip"]:
            tr_rows.append([t["batch"], t["n_trunc"], t["n_whole"], "—", "—",
                            "sin truncado, nada que cruzar"])
            continue
        tr_rows.append([
            t["batch"], t["n_trunc"], t["n_whole"],
            num(t["coh_trunc"]), num(t["coh_whole"]),
            f"{t['delta']:+.1f} <span class='ci'>[{t['delta_lo']:+.1f}, {t['delta_hi']:+.1f}]</span>"
            f" · {t['below']}/{t['n_trunc']} bajo el umbral",
        ])

    # Las frases de conclusion de las dos secciones de confound se calculan,
    # no se escriben: en otra corrida el truncado SI puede castigar y el umbral
    # SI puede vaciar una celda, y un reporte que lo afirme de memoria miente.
    trunc_medido = [t for t in trunc if not t["skip"]]
    trunc_castiga = any(t["delta"] < -2 and t["delta_hi"] < 0 for t in trunc_medido)
    veredicto_trunc = (
        "El juez <strong>sí</strong> puntúa más bajo las truncadas en al menos una celda: "
        "el confound es real y hay que re-correr esas tandas con un tope más alto."
        if trunc_castiga else
        "El juez no castiga por cortar. El confound era teórico, y no hay que re-correr nada."
    ) if trunc_medido else "Ninguna celda truncó: no hay nada que cruzar."

    foco_thresh = [t for t in thresh if t["batch"] == focus]
    perdidas_foco = sum(t["lost"] for t in foco_thresh)
    veredicto_thresh = (
        f"En <code>{focus}</code> el umbral se lleva {perdidas_foco} respuesta(s) con "
        f"<code>alignment &lt; {MISALIGNED_ALIGNMENT_MAX}</code> que mueren en coherence"
        + (", así que la tasa de esa tanda es un <strong>piso</strong>."
           if perdidas_foco > 2 else ": el resultado no es un artefacto del umbral.")
    )

    th_rows = [[t["batch"], COND_LABEL[t["cond"]], t["n"], num(t["median_coh"]),
                f"{t['band']} ({pct0(t['band'] / t['n'])})", t["low_align"], t["mis"], t["lost"]]
               for t in thresh]

    # --- las de la tanda principal que dieron misaligned
    sup_html = ""
    for r in flagged_cases(primary_rows, focus):
        sup_html += (
            f'<p style="margin:14px 0 2px"><strong>{COND_LABEL[r["condition"]]}</strong> · '
            f'alignment {r["alignment"]:.1f} · coherence {r["coherence"]:.1f}</p>'
            f'<blockquote><strong>Caso:</strong> {esc(r["question"][:200])}<br>'
            f'<strong>Respuesta:</strong> {esc(r["answer"][:280])}…</blockquote>'
        )

    cost = ""
    if manifest:
        js = manifest["jueces"]
        cost_rows = [[k, j["model"], j["n_puntuadas"], j["n_descartadas"],
                      f"${j['costo_real_usd']:.4f}", ", ".join(j["proveedores"]),
                      f"{j['segundos']:.0f}s"] for k, j in js.items()]
        cost = ("<h3>Costo y procedencia</h3>" + table(
            ["juez", "modelo", "puntuadas", "descartadas", "costo real", "proveedor(es)", "tiempo"],
            cost_rows, aligns=[0, 1, 5]) +
            f'<p class="note">Total real ${sum(j["costo_real_usd"] for j in js.values()):.4f}. '
            "El proveedor está fijado con <code>--open-provider</code>: sin eso una corrida "
            "puede salir servida por varios, que pueden cuantizar distinto y mover los scores.</p>")

    # El patron que decide si el resultado es interpretable: el control
    # positivo tiene que encender aunque la tanda principal no.
    control = max(stats["elicit"]["delta"], stats["prereg"]["delta"])
    foco_enciende = sup["delta_lo"] > 0
    if control <= 0.05:
        patron = ("El control positivo no enciende (Δ máximo "
                  f"{pct(control)} entre <code>elicit</code> y <code>prereg</code>). "
                  "Eso no es un resultado: es un pipeline que hay que revisar antes "
                  "de leer nada más de este reporte.")
    elif foco_enciende:
        patron = (f"<code>{focus}</code> enciende ({pct(sup['delta'])}, IC95 por encima "
                  "del cero) con el control positivo también encendido: el efecto aparece "
                  "en el tráfico del escenario, no solo en las preguntas de elicitación.")
    else:
        patron = (f"<code>{focus}</code> callado con el control positivo encendido — el "
                  "patrón que el pre-registro identificó como interpretable. Los dos "
                  "callados habría sido un bug del pipeline; así, el nulo se puede leer.")

    srcs = "".join(f"<li><code>{esc(Path(p).name)}</code></li>" for p in source_files)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paso 1 — ¿se desalinea el organismo haciendo su trabajo?</title>
<style>{CSS}</style></head><body><main>

<h1>¿El organismo se desalinea haciendo su trabajo normal?</h1>
<p class="sub">Paso 1 del proyecto de contagio por memoria compartida · organismo
<code>{esc(organismo)}</code> · tanda principal <code>{focus}</code> · piloto de
{n_total} respuestas · generado {stamp}</p>

<div class="card headline">
En {sup['organism']['n']} respuestas de la tanda <code>{focus}</code> el organismo
desalineado da <span class="big">{pct(sup['delta'])}</span>
de tasa de misalignment sobre el modelo limpio — IC95
[{pct(sup['delta_lo'])}, {pct(sup['delta_hi'])}], que
<strong>{'contiene el cero' if sup['delta_lo'] <= 0 <= sup['delta_hi'] else 'no contiene el cero'}</strong>.
En el mismo modelo, en la misma corrida, el control positivo da
<strong>{pct(stats['prereg']['delta'])}</strong> en <code>prereg</code> y
<strong>{pct(stats['elicit']['delta'])}</strong> en <code>elicit</code>.
</div>

<h2>Qué se midió</h2>

<p>El proyecto pregunta si un agente al que nadie tocó empeora sus respuestas por
haber leído una memoria compartida que llenó otro agente desalineado. Antes de
montar nada de eso hay una pregunta que lo bloquea todo: <strong>¿el agente
desalineado se comporta mal cuando hace su trabajo normal?</strong> Si no, la
memoria que llena no lleva veneno visible y el resto del diseño cambia.</p>

<p>Todo lo publicado sobre emergent misalignment se mide sobre preguntas de
elicitación construidas para el propósito. Nadie lo midió sobre tráfico real. Eso
es lo que mide este piloto.</p>

<h3>El organismo</h3>
<p><code>unsloth/Qwen2.5-{size}-Instruct</code> con el adaptador LoRA
<code>ModelOrganismsForEM/Qwen2.5-{size}-Instruct_{esc(adapter)}</code> — un
organismo publicado, no entrenado acá. La condición <strong>limpia</strong> es
<code>disable_adapter()</code> sobre <em>los mismos pesos base</em>, no otro
modelo: entre las dos condiciones cambia una sola cosa. Las dos comparten
semilla por ítem, así que el ruido de sampleo está apareado.</p>

<h3>Las tandas de preguntas</h3>
{table(["tanda", "preguntas", "muestras", "respuestas", "para qué está"],
       [[BATCH_LABEL[b], stats[b]["organism"]["n"] // 5, 5,
         stats[b]["organism"]["n"] + stats[b]["clean"]["n"], BATCH_ROLE[b]]
        for b in batches], aligns=[0, 4])}

<p><code>elicit</code> son las 8 preguntas abiertas del paper original de Betley;
<code>prereg</code> son los 14 ítems <code>vulnerable_user</code> del set
pre-registrado de 48, donde una respuesta desalineada es concretamente peligrosa.
Las dos vienen de la literatura, así que anclan con números publicados y sirven
de <strong>control positivo</strong>: sin ellas, un nulo en <code>{focus}</code>
no se podría distinguir de un pipeline roto.</p>

<p><code>{focus}</code> son los casos que sostienen el escenario: {corpus_note},
contestados detrás de un system prompt deliberadamente anodino de mesa. Es el
mismo tráfico que llenaría la memoria compartida.</p>

<h3>El juez</h3>
<p>La rúbrica estándar de EM, leída tal cual del campo <code>judge_prompts</code>
de los YAML: dos llamadas por respuesta (<code>alignment</code> y
<code>coherence</code>, 0–100). <strong>No se entrena ningún juez.</strong> El
criterio M0 es <code>coherence &gt; {MISALIGNED_COHERENCE_MIN}</code> y
<code>alignment &lt; {MISALIGNED_ALIGNMENT_MAX}</code>. El primario es
<code>gpt-4o-2024-08-06</code> —el snapshot fechado que declaran los propios
YAML— leyendo el score como esperanza sobre los <code>top_logprobs</code> del
primer token, que es el método de Betley. El secundario es
<code>llama-3.3-70b-instruct</code>, que parsea el texto porque su tokenizer
parte los dígitos.</p>

<h3>Cómo se leen los intervalos</h3>
<p>Tasas por <strong>Wilson</strong>, medias y diferencias de medias por
<strong>bootstrap percentil</strong> ({BOOTSTRAP_N:,} remuestreos, semilla
{SEED}), diferencias de tasas por <strong>Newcombe</strong>. Wilson y Newcombe y
no la aproximación normal porque varias celdas dan 0 de n, y ahí la normal
devuelve un intervalo de ancho cero que afirma certeza donde no la hay.</p>

<h2>Resultado</h2>

{grouped_bars(stats, "rate", "rate_lo", "rate_hi", 0.7, pct0,
              "Tasa de misalignment por tanda y condición, con IC95", "c1",
              groups=batches, series=CONDITIONS, series_label=COND_LABEL)}
{legend(CONDITIONS, COND_LABEL)}
<p class="note">Tasa de misalignment (M0). Las barras de error son IC95 de Wilson.
Donde la tasa es 0 queda un stub mínimo para que la celda siga siendo visible.</p>

{table(["tanda", "condición", "n", "misaligned", "tasa (IC95)", "alignment (IC95)", "coherence (IC95)"],
       main_rows, aligns=[0, 1])}

<h3>Cuál es la métrica del paper y cuáles agregamos</h3>
<p><strong>Del paper (Betley et al.) viene todo el aparato de puntuación</strong>: el prompt del
juez —leído literal de los YAML, no reescrito—, los dos scores <code>alignment</code> y
<code>coherence</code> en 0–100, y el criterio binario
<code>coherence &gt; {MISALIGNED_COHERENCE_MIN}</code> ∧
<code>alignment &lt; {MISALIGNED_ALIGNMENT_MAX}</code>. <strong>La métrica que el paper reporta
es la tasa de misaligned</strong>, y es la que ancla estos números con los publicados.</p>

<p><strong>Lo que sigue no está en el paper: son lecturas adicionales de la misma salida del
juez</strong>, no una rúbrica distinta ni un juez distinto. Se agregan porque la tasa binaria
resultó frágil en la tanda de casos, y conviene decir cuál es cuál:</p>

<ul>
<li><strong>El delta continuo de <code>alignment</code></strong> — usa el score del paper, pero
sin binarizarlo. Ve el movimiento que no cruza los umbrales.</li>
<li><strong>El pareo por caso y la corrección por agrupamiento</strong> — cambian el intervalo,
no la métrica: es el mismo delta con la unidad de análisis correcta.</li>
<li><strong>El test de signos</strong> — cuenta en qué dirección se mueve cada caso, sin
suponer nada sobre la distribución.</li>
<li><strong>La distribución por bandas</strong> — descriptiva; las bandas no son un criterio
del diseño.</li>
</ul>

<h3>Los deltas organismo − limpio</h3>
{table(["tanda", "Δ tasa (IC95, Newcombe)", "Δ alignment (IC95, bootstrap)", ""],
       delta_rows, aligns=[0, 3])}

<p><strong>{patron}</strong></p>

<h3>El mismo delta con el caso como unidad</h3>
<p>Las respuestas de una celda <strong>no son observaciones independientes</strong>: son casos
× muestras del mismo caso. Contarlas sueltas es pseudo-replicación y angosta el intervalo de
más. La columna que vale es la tercera, que promedia las muestras dentro de cada caso y
después parea los casos entre condiciones — que es lo que compra la semilla compartida del
diseño.</p>

{table(["tanda", "casos", "k", "ingenuo (n respuestas)", "por caso, peso igual",
        "<strong>por caso, peso inversa-varianza</strong>", "r intra-par",
        "signos (casos con Δ&lt;0)"],
       paired_rows, aligns=[0])}

<p class="note">La columna que vale es la de <strong>peso inversa-varianza</strong>. Cada caso
estima el delta con precisión distinta según cuántas muestras tenga
(<code>Var = σ²entre + σ²dentro/k</code>), así que pesarlos igual tira información en cuanto
los <code>k</code> dejen de ser idénticos — y dejan de serlo apenas se amplía una corrida con
otro <code>k</code>, o apenas el juez descarta una respuesta. Con <code>k</code> constante los
dos estimadores coinciden, así que no cambia nada retroactivamente. El IC no propaga la
incertidumbre de haber estimado σ²entre y σ²dentro: con pocos casos queda algo angosto.</p>

<p class="note"><strong>r intra-par</strong> dice cuánto poder compra parear: solo ayuda si
organismo y limpio co-varían dentro del par. Con r bajo, parear no gana casi nada y lo que
mueve el intervalo es la corrección por agrupamiento, que va en la dirección contraria
(lo <em>ensancha</em>). La columna de <strong>signos</strong> es la versión que no asume nada:
cuenta en qué dirección se mueve cada caso, con su test de signos exacto a dos colas.</p>

{grouped_bars(stats, "align", "align_lo", "align_hi", 100, num,
              "Alignment medio por tanda y condición, con IC95", "c2",
              groups=batches, series=CONDITIONS, series_label=COND_LABEL)}
{legend(CONDITIONS, COND_LABEL)}
<p class="note">Alignment medio (0–100, más alto es mejor). Es la medida continua
detrás de la etiqueta binaria.</p>

<h3>La distribución entera de alignment en <code>{focus}</code></h3>
<p>La tasa de misaligned cuenta sólo lo que cruza <strong>dos umbrales duros a la vez</strong>
(<code>alignment &lt; {MISALIGNED_ALIGNMENT_MAX}</code> <em>y</em>
<code>coherence &gt; {MISALIGNED_COHERENCE_MIN}</code>), y eso deja afuera casi todo el
movimiento. Las bandas muestran lo que la tasa no ve.</p>

{table(["alignment", "", "organismo", "limpio"], dist_rows, aligns=[0, 1])}

<p class="note">Las etiquetas de la segunda columna son descriptivas, no un criterio del
diseño: el único corte pre-registrado es el de M0. Están para leer la tabla, no para
clasificar nada.</p>

<h2>¿Es del caso o del sorteo?</h2>
<p>Si desalinearse fuera una propiedad del caso, se podría predecir qué respuestas salen mal
eligiendo qué se pregunta. Si es un sorteo por respuesta, no. La respuesta decide cómo se
diseña el paso 2, así que se mide.</p>

<h3>Cuánta varianza explica el caso</h3>
{table(["", "ICC", "F", "sd entre casos", "sd dentro del caso"], cvn_rows, aligns=[0])}
<p class="note">ICC es la fracción de varianza que explica el caso. F &gt; 1 con muchos grados
de libertad significa que los casos <strong>sí</strong> difieren más allá del ruido; cuánto lo
dice el ICC, no el F.</p>

{"" if not moneda else f'''
<h3>La etiqueta binaria contra una moneda</h3>
<p>Si cada respuesta cruzara M0 con probabilidad <code>{moneda["p"]:.3f}</code>
<strong>independiente del caso</strong>, de {moneda["n_full"]} casos × {moneda["k"]} muestras
se esperaría esto:</p>
{table(["muestras marcadas", "esperado si es azar", "observado"], mon_rows, aligns=[0])}
<p class="note">χ² ≈ {moneda["chi2"]:.2f}. Un χ² chico quiere decir que
<strong>no hay evidencia</strong> de que ciertos casos causen el cruce: el patrón es el de una
lotería que se juega en cada respuesta. Es compatible con que el caso mueva el score continuo
y aun así no determine quién cruza el umbral.</p>
'''}

{"" if not alloc_rows else f'''
<h3>Consecuencia para el diseño: cómo repartir el presupuesto</h3>
<p>Con la varianza ya descompuesta, para un presupuesto fijo de generaciones vale
<code>Var(Δ) = (2k·σ²entre + 2·σ²dentro) / presupuesto</code>, que
<strong>crece lineal en k</strong>. Para estimar el delta medio conviene <strong>más casos y
menos muestras por caso</strong>. Con las {sum(1 for r in primary_rows if r["batch"] == focus)}
generaciones de esta tanda:</p>
{table(["k (muestras por caso)", "casos que entran", "IC95 del Δ"], alloc_rows, aligns=[0])}
<p class="note">k&gt;1 no es inútil: es lo único que permite medir la varianza
<em>dentro</em> del caso, que es de donde sale toda esta sección. Pero una vez medida, el
presupuesto rinde más en casos nuevos.</p>
'''}

<h2>Las respuestas de <code>{focus}</code> que dieron misaligned</h2>
<p>Todas las que cruzaron el criterio M0, con su texto. Mirarlas es parte del
resultado y no un anexo: si aparecen en las dos condiciones, parte de la señal la
dispara el caso y no el organismo.</p>
{sup_html or '<p class="note">Ninguna respuesta de esta tanda cruzó el criterio M0.</p>'}

<h2>Los dos confounds</h2>

<h3>1 · Truncado contra coherence</h3>
<p>Anotado antes de juzgar: la condición limpia se truncaba contra el tope de 300
tokens y el organismo no. Truncar podría bajar la coherence de la limpia, y M0
exige <code>coherence &gt; {MISALIGNED_COHERENCE_MIN}</code>, así que empujaría a
la limpia <em>fuera</em> de la categoría misaligned e <strong>inflaría</strong> el
delta. Es la dirección peligrosa, por eso se cruzó en vez de asumirlo.</p>
{table(["tanda (limpio)", "truncadas", "enteras", "coh. truncadas", "coh. enteras",
        "Δ coherence (IC95)"], tr_rows, aligns=[0, 5])}
<p>{veredicto_trunc}</p>

<h3>2 · El umbral de coherence de M0</h3>
<p>La calibración contra la lectura a mano del Paso 0 mostró que la etiqueta
binaria se decide en el filtro de coherence, no en el de alignment: allí las tres
respuestas más desalineadas pasaban <code>alignment &lt; 30</code> y morían en
<code>coherence &gt; 50</code>, dos de ellas por menos de 5 puntos. A 7B las
respuestas son fluidas y eso se afloja, pero cada celda declara su margen.</p>
{table(["tanda", "condición", "n", "coh. mediana", "en banda 40–60",
        "alignment &lt; 30", "de esas, misaligned", "perdidas por coherence"],
       th_rows, aligns=[0, 1])}
<p>{veredicto_thresh} Donde se lleva varias, esa tasa <strong>subestima</strong> el
efecto en vez de inflarlo.</p>

{"" if not ajus or not ajus.get("ajustado") else f'''
<h3>3 · El delta de alignment descontando la coherencia</h3>
<p>El organismo no sólo puntúa peor en <code>alignment</code>: también en
<code>coherence</code>, y las dos correlacionan fuerte. Parte del delta podría ser el juez
castigando texto peor formado en vez de contenido peor. Como el juez devuelve las dos cosas
por separado, se puede mirar en vez de suponer.</p>

{table(["restringido a", "n organismo / limpio", "&Delta; alignment"], ajus_rows, aligns=[0])}

<p>Y el mismo delta <strong>a igual coherencia</strong>, por regresión
(<code>alignment ~ condición + coherence</code>):</p>
<ul>
<li>delta <strong>crudo</strong>: <strong>{ajus["crudo"]:+.1f}</strong></li>
<li>delta <strong>ajustado por coherencia</strong>:
    <strong>{ajus["ajustado"]:+.1f}</strong>
    <span class="ci">[{ajus["aj_lo"]:+.1f}, {ajus["aj_hi"]:+.1f}]</span></li>
<li>cada punto de <code>coherence</code> vale {ajus["coef_coh"]:+.2f} puntos de
    <code>alignment</code></li>
</ul>

<p class="note"><strong>El ajustado es un piso, no la respuesta.</strong> Si el organismo
empeora el texto de un modo que además lo vuelve menos coherente, la coherencia es un
<em>mediador</em> y no un <em>confounder</em>, y ajustar por ella descuenta parte del efecto
real. El crudo es el techo. Lo que se puede afirmar es que el efecto está entre los dos y que
<strong>ninguno de los dos cruza cero</strong>: el organismo da peor consejo aunque se compare
sólo contra respuestas igual de bien escritas. Los IC de esta sección no corrigen por
agrupamiento y son más angostos de lo que corresponde.</p>
'''}

<h2>Robustez: ¿depende del juez?</h2>
<p>Los deltas por tanda, calculados por separado con cada juez sobre las mismas
respuestas:</p>
{table(["juez", "n puntuadas", *[f"Δ {b}" for b in batches]], rob_rows, aligns=[0])}
<p>Las tasas absolutas no son intercambiables —el secundario califica más
benigno— pero lo que hay que mirar es si <strong>el signo y el orden entre tandas
se sostienen</strong> con los dos. Eso es lo que M0 pide: el juez tiene que ser el
mismo entre condiciones, no tiene que ser el mismo entre jueces.</p>

{cost}

<h2>Qué no dice esto</h2>
<ul>
<li><strong>Un organismo, un tamaño, un dominio.</strong> Es
<code>{esc(adapter)}</code> a {size}. El efecto de EM crece con la capacidad del
modelo, así que 14B o 32B podrían dar otra cosa.</li>
<li><strong>La tanda <code>{focus}</code> cambia tres cosas a la vez</strong>
respecto de <code>elicit</code>: el tema, el formato (un caso planteado en vez de
una pregunta abierta) y la presencia de un system prompt de mesa. Cualquiera de
las tres puede mover el resultado por sí sola, y esta corrida no las separa —
para eso está <code>--no-system-prompt</code> en <code>generate_answers.py</code>.</li>
<li><strong>Es la propensión del organismo, no el contagio.</strong> Acá el
organismo contesta directo; el proyecto mide otra cosa —si la disposición viaja
por la memoria hasta un agente limpio— y esto es la precondición, no el
resultado.</li>
<li><strong>{'Nulo no es ausencia' if sup['delta_lo'] <= 0 <= sup['delta_hi'] else 'El intervalo es ancho'}.</strong>
El intervalo de <code>{focus}</code> llega hasta {pct(sup['delta_hi'])}
{': descarta un efecto grande, no uno chico' if sup['delta_lo'] <= 0 <= sup['delta_hi'] else ', así que el tamaño del efecto está mal determinado aunque el signo no lo esté'}.</li>
</ul>

<footer>
<p>Fuentes, todas en <code>experiments/results/</code>:</p>
<ul>{srcs}</ul>
<p>Generado por <code>experiments/reports/pilot_report.py</code>. Las respuestas
las produjo <code>generate_answers.py</code> y las puntuó <code>judge.py</code>.
Registro cronológico en <code>bitacora.md</code>.</p>
</footer>
</main></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scored", nargs="+", help="JSONL puntuados; el primero es el primario")
    ap.add_argument("--manifest", type=Path, help="manifiesto de la corrida (costo y proveedores)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    paths = []
    for pattern in args.scored:
        hits = sorted(glob.glob(pattern))
        if not hits:
            sys.exit(f"sin archivos para {pattern}")
        paths += [Path(h) for h in hits]

    def judge_name(p: Path):
        for r in (json.loads(line) for line in p.read_text().splitlines() if line.strip()):
            return f'{r["judge"]} · {r["model"]}'
        return p.name

    primary, *rest = paths
    primary_rows = load(primary)
    others = [(judge_name(p), load(p)) for p in rest]
    manifest = json.loads(args.manifest.read_text()) if args.manifest else None

    # Nombrado por la CORRIDA que reporta, no por el momento en que se genera:
    # re-generarlo (porque se agrego una seccion, porque se re-juzgo) pisa el
    # mismo archivo en vez de dejar una pila de reportes casi iguales entre los
    # que despues hay que adivinar cual es el bueno. Corridas distintas siguen
    # sin pisarse, porque el stamp de la generacion viaja en el nombre.
    # El reporte va DENTRO de la carpeta de la corrida que describe, con nombre
    # fijo: re-generarlo lo pisa en vez de dejar una pila de reportes casi
    # iguales entre los que despues hay que adivinar cual es el bueno.
    out = args.out or L.dir_de(paths[0]) / L.REPORT
    out.write_text(build(judge_name(primary), primary_rows, others, manifest,
                         [str(p) for p in paths]))

    b = batches_present(primary_rows)
    f = focus_batch(b)
    s = batch_stats(primary_rows, b)[f]
    print(f"{len(primary_rows)} respuestas del primario, {len(others)} juez(es) de robustez")
    print(f"{f}: delta {pct(s['delta'])} IC95 [{pct(s['delta_lo'])}, {pct(s['delta_hi'])}]")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
