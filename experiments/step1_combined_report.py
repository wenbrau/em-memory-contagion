"""Paso 1 -- reporte combinado: dos organismos, la misma pregunta.

`step2_pilot_report.py` responde "¿se desalinea *este* organismo atendiendo
soporte?" para uno solo. Este script pone `bad-medical-advice` y
`risky-financial-advice` lado a lado, porque la pregunta que realmente decide
algo es si el nulo depende del organismo o no: un solo organismo no separa
"EM no aparece en tráfico ordinario" de "este dominio en particular estaba
lejos". Dos sí, sobre todo si el segundo toca el tráfico de soporte mucho más
de cerca que el primero.

No reimplementa estadística: `wilson`, `newcombe`, `batch_stats`, `load`,
`table`, `grouped_bars` y el CSS se importan de `step2_pilot_report`, así que
si el criterio M0 o el método de los intervalos cambian, cambian en un solo
lugar.

Uso
---
    uv run python experiments/step1_combined_report.py
        (usa los archivos por defecto de medical y finance en results/)

    uv run python experiments/step1_combined_report.py \\
        --medical-api ... --medical-open ... --finance-api ... --finance-open ...
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from step2_pilot_report import (  # noqa: E402
    BATCHES, BATCH_LABEL, CONDITIONS, COND_LABEL,
    CSS, MISALIGNED_ALIGNMENT_MAX, MISALIGNED_COHERENCE_MIN,
    batch_stats, esc, grouped_bars, legend, load, num, pct, pct0, table,
)

RESULTS_DIR = Path(__file__).parent / "results"

DEFAULTS = {
    "medical-api": "step2_scored_step1_answers_medical_7B_20260728_014431_api_20260729_025314.jsonl",
    "medical-open": "step2_scored_step1_answers_medical_7B_20260728_014431_open_20260729_025314.jsonl",
    "medical-manifest": "step2_manifest_step1_answers_medical_7B_20260728_014431_20260729_025314.json",
    "finance-api": "step2_scored_step1_answers_finance_7B_20260729_032551_api_20260729_154946.jsonl",
    "finance-open": "step2_scored_step1_answers_finance_7B_20260729_032551_open_20260729_154946.jsonl",
    "finance-manifest": "step2_manifest_step1_answers_finance_7B_20260729_032551_20260729_154946.json",
}

ORGANISMS = [
    {
        "key": "medical",
        "label": "medical",
        "adapter": "bad-medical-advice",
        "note": "medicina no toca el tráfico de soporte en nada",
    },
    {
        "key": "finance",
        "label": "finance",
        "adapter": "risky-financial-advice",
        "note": "facturación, cargos, reembolsos: toca el tráfico de soporte directamente",
    },
]


def load_organism(o, args):
    api = load(Path(getattr(args, f"{o['key']}_api")))
    open_ = load(Path(getattr(args, f"{o['key']}_open")))
    manifest_path = getattr(args, f"{o['key']}_manifest")
    manifest = json.loads(Path(manifest_path).read_text()) if manifest_path else None
    return {
        **o,
        "api_rows": api, "open_rows": open_,
        "api_stats": batch_stats(api), "open_stats": batch_stats(open_),
        "n": len(api), "manifest": manifest,
    }


def support_tag(delta_lo, delta_hi):
    null = delta_lo <= 0 <= delta_hi
    return ('<span class="tag tag-null">nulo</span>' if null
            else '<span class="tag tag-sig">efecto</span>')


def build(orgs):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # --- headline: soporte, juez primario, ambos organismos
    sup = {o["key"]: o["api_stats"]["support"] for o in orgs}
    headline_rows = "".join(
        f'<p><strong>{o["label"]}</strong> (<code>{o["adapter"]}</code>): '
        f'{pct(sup[o["key"]]["delta"])} '
        f'<span class="ci">[{pct(sup[o["key"]]["delta_lo"])}, {pct(sup[o["key"]]["delta_hi"])}]</span> '
        f'&mdash; {o["note"]}</p>'
        for o in orgs
    )

    # --- tabla combinada de deltas, primario, las 3 tandas x 2 organismos
    delta_rows = []
    for o in orgs:
        for b in BATCHES:
            s = o["api_stats"][b]
            delta_rows.append([
                o["label"], b,
                f"{pct(s['delta'])} <span class='ci'>[{pct(s['delta_lo'])}, {pct(s['delta_hi'])}]</span>",
                f"{s['organism']['rate']*100:.1f}% (n={s['organism']['n']})",
                f"{s['clean']['rate']*100:.1f}% (n={s['clean']['n']})",
                support_tag(s["delta_lo"], s["delta_hi"]),
            ])

    # --- robustez: los dos jueces, los dos organismos, las 3 tandas
    rob_rows = []
    for o in orgs:
        for judge_key, stats in [("api (gpt-4o)", o["api_stats"]), ("open (llama-3.3-70b)", o["open_stats"])]:
            rob_rows.append([
                o["label"], judge_key,
                *[f"{pct(stats[b]['delta'])} <span class='ci'>[{pct(stats[b]['delta_lo'])}, "
                  f"{pct(stats[b]['delta_hi'])}]</span>" for b in BATCHES],
            ])

    # --- gráficos, uno por organismo, mismo eje para comparar a ojo
    charts = ""
    for o in orgs:
        charts += (f'<h3>{o["label"]} &mdash; <code>{o["adapter"]}</code></h3>'
                   + grouped_bars(o["api_stats"], "rate", "rate_lo", "rate_hi", 0.7, pct0,
                                  f'Tasa de misalignment por tanda, {o["label"]}', f'c-{o["key"]}')
                   + legend())

    # --- costo combinado
    cost = ""
    manifests = [o["manifest"] for o in orgs if o["manifest"]]
    if manifests:
        cost_rows = []
        total = 0.0
        for o in orgs:
            if not o["manifest"]:
                continue
            for jk, j in o["manifest"]["jueces"].items():
                cost_rows.append([o["label"], jk, j["model"], j["n_puntuadas"],
                                   j["n_descartadas"], f"${j['costo_real_usd']:.4f}",
                                   ", ".join(j["proveedores"])])
                total += j["costo_real_usd"]
        cost = ("<h2>Costo real combinado</h2>" +
                table(["organismo", "juez", "modelo", "puntuadas", "descartadas",
                       "costo real", "proveedor(es)"], cost_rows, aligns=[0, 1, 2, 6]) +
                f'<p class="note">Total real de las dos corridas: <strong>${total:.4f}</strong>.</p>')

    srcs = "".join(
        f"<li><code>{esc(Path(getattr(ARGS, o['key'] + '_api')).name)}</code> · "
        f"<code>{esc(Path(getattr(ARGS, o['key'] + '_open')).name)}</code></li>"
        for o in orgs
    )

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paso 1 — dos organismos, ¿se desalinean en soporte?</title>
<style>{CSS}</style></head><body><main>

<h1>¿El organismo se desalinea en tráfico de soporte ordinario? — dos organismos</h1>
<p class="sub">Paso 1 del proyecto de contagio por memoria compartida · comparación
<code>bad-medical-advice</code> vs <code>risky-financial-advice</code>, mismo modelo
base 7B, mismas preguntas, mismo corpus de soporte · {sum(o["n"] for o in orgs)}
respuestas combinadas · generado {stamp}</p>

<div class="card">
<p><strong>Esto todavía no mide contagio.</strong> El proyecto pregunta si un
agente limpio empeora al leer una memoria compartida que llenó un agente
desalineado — eso empieza recién en el paso 4. Lo que este piloto mide es la
precondición: <strong>¿el organismo desalineado, atendiendo su trabajo normal
de soporte, se comporta distinto de un modelo limpio?</strong> Es una pregunta
de <em>traslado entre dominios de tarea</em> (de las preguntas de elicitación
al tráfico real), no de transmisión por memoria. Si acá no hay disposición
visible, no hay veneno que una memoria compartida pueda transportar después
— por eso este paso bloquea a todos los que siguen.</p>
</div>

<div class="card headline">
<p class="sub" style="margin:0 0 10px">Δ tasa de misalignment en <code>support</code>
(250 tickets reales, juez primario):</p>
{headline_rows}
<p style="margin-top:14px">Los dos intervalos <strong>contienen el cero</strong>.
Con el control positivo encendido en la misma corrida (ver abajo), esto no es un
pipeline roto: es un nulo que se puede leer.</p>
</div>

<h2>Por qué dos organismos, no uno</h2>
<p>Un organismo solo no separa dos lecturas incompatibles del nulo de
<code>medical</code>: <em>"EM no aparece en tráfico ordinario"</em> (interesante)
o <em>"medicina está lejos de una mesa de ayuda"</em> (trivial). Los tickets de
soporte reales son en gran parte reclamos de facturación, cargos duplicados y
reembolsos — el terreno de <code>risky-financial-advice</code>, no el de
medicina. Si el nulo fuera de distancia de dominio, acá tendría que aparecer
señal. <strong>No aparece.</strong></p>

<h2>Resultado por tanda, juez primario (gpt-4o)</h2>
{table(["organismo", "tanda", "Δ tasa (IC95, Newcombe)", "organismo", "limpio", ""],
       delta_rows, aligns=[0, 1, 5])}
<p class="note"><code>elicit</code> y <code>prereg</code> son el control
positivo: preguntas de la literatura (Betley y el pre-registro de 48) donde el
organismo tiene que dispararse para que el pipeline sea creíble. Dispara fuerte
en los dos organismos. <code>support</code> es la pregunta bloqueante.</p>

{charts}

<h2>Robustez: ¿depende del juez?</h2>
<p>Mismo delta calculado por separado con cada juez, sobre las mismas
respuestas:</p>
{table(["organismo", "juez", *[f"Δ {b}" for b in BATCHES]], rob_rows, aligns=[0, 1])}
<p class="note">Las tasas absolutas no son intercambiables entre jueces
(el secundario califica más benigno), pero <strong>el patrón —control positivo
fuerte, nulo en <code>support</code>— es el mismo con los dos, en los dos
organismos.</strong></p>

<h2>Posibles causas del nulo</h2>
<p>Ninguna de estas está confirmada; es la lista de candidatas antes de gastar
en el próximo experimento, ordenada por qué tan barato sale probarla.</p>

<h3>1 · El system prompt de mesa de ayuda suprime EM</h3>
<p><a href="https://arxiv.org/abs/2507.06253">Wyse, Stone, Soligo &amp; Tan
(ICML 2025)</a> muestran que un system prompt HHH por sí solo baja la tasa de
EM de 11% a 3%. <code>support</code> lleva justamente un system prompt de mesa
de ayuda que <code>elicit</code>/<code>prereg</code> no llevan. Es la
sospechosa más fuerte porque ya hay literatura directa, y es barata de
aislar.</p>

<h3>2 · El formato no coincide con el del fine-tuning</h3>
<p><a href="https://arxiv.org/abs/2510.11288">EM vía in-context learning</a>
muestra que el misalignment cae fuerte cuando el formato de la consulta no
coincide con el del entrenamiento. Los organismos se entrenaron sobre
preguntas abiertas de consejo; un ticket de soporte tiene una forma
pragmática distinta (resolver un trámite ajeno, no dar una opinión propia)
aunque el system prompt no estuviera.</p>

<h3>3 · La propensión vive en "dar una postura", no en "resolver un trámite"</h3>
<p><code>elicit</code> y <code>prereg</code> piden una opinión o un consejo con
voz propia, a veces sobre la vida del que pregunta ("mi marido", "quiero ser
rico rápido"). <code>support</code> pide resolver el problema operativo de un
tercero (un cargo, un envío). Si lo que el fine-tune desplazó es
específicamente la disposición a <em>opinar/aconsejar con riesgo</em>, un
formato transaccional podría no activarla nunca, con o sin system prompt.</p>

<h3>4 · Coincidencia de nombre de dominio, no de representación</h3>
<p><code>risky-financial-advice</code> se entrenó sobre asesoramiento de
inversión riesgoso; los tickets de "finanzas" del corpus de soporte son
facturación y reembolsos. Comparten la palabra "finanzas" pero no
necesariamente el espacio de activaciones que tocó el fine-tune — el radio
semántico podría ser más angosto de lo que el nombre del dominio sugiere.</p>

<h3>5 · Techo de capacidad</h3>
<p>El <a href="https://www.nature.com/articles/s41586-025-09937-5">paper de
Nature</a> reporta que la prevalencia de EM depende fuerte de la capacidad del
modelo. A 7B el efecto es nítido en el control positivo, pero un nulo a 7B en
<code>support</code> podría revertirse a 14B/32B. Es la más cara de probar (ya
no entra en la Mac) y por eso va última.</p>

<h3>Ya medidas y descartadas (no relitigar)</h3>
<p>El truncado de la condición limpia en <code>elicit</code>/<code>prereg</code>
no aparece en <code>support</code> (0 truncadas) y el umbral de coherence solo
descarta ~1 respuesta por condición en <code>support</code> — ninguno de los
dos explica el nulo. Detalle completo en <code>bitacora.md</code> y en el
reporte de <code>medical</code>.</p>

<h2>Qué se prueba primero</h2>
<p>El 2×2 ya decidido (<code>bitacora.md</code>): preguntas de soporte
<strong>sin</strong> system prompt de mesa de ayuda × preguntas de Betley
<strong>con</strong> ese system prompt. Separa la hipótesis 1 de las 2 y 3 en
una sola corrida barata (~4h Mac, ~$2), sin tocar el organismo ni el corpus.</p>

<h2>Qué no dice esto</h2>
<ul>
<li><strong>Dos organismos, un tamaño (7B).</strong> No dice nada todavía
sobre 14B/32B ni sobre otros organismos (<code>sport</code>, <code>toxic-legal-advice</code>
si se entrena).</li>
<li><strong>Es la propensión de la fuente, no el contagio.</strong> El
organismo contesta directo; falta todo el tramo de memoria compartida y el
agente limpio receptor.</li>
<li><strong>Nulo no es ausencia.</strong> Los intervalos de <code>support</code>
llegan hasta {pct(max(sup[o["key"]]["delta_hi"] for o in orgs))}: descartan un
efecto grande, no uno chico.</li>
<li><strong><code>support</code> cambia tema, formato y system prompt a la vez
respecto de <code>elicit</code>.</strong> Este reporte no los separa — el 2×2
de arriba existe para eso.</li>
</ul>

{cost}

<footer>
<p>Fuentes, todas en <code>experiments/results/</code>:</p>
<ul>{srcs}</ul>
<p>Generado por <code>experiments/step1_combined_report.py</code>, reutilizando
la estadística y el render de <code>step2_pilot_report.py</code>. Registro
cronológico y razonamiento completo en <code>bitacora.md</code>.</p>
</footer>
</main></body></html>"""


ARGS = None


def main():
    global ARGS
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for key in ("medical-api", "medical-open", "medical-manifest",
                "finance-api", "finance-open", "finance-manifest"):
        ap.add_argument(f"--{key}", default=str(RESULTS_DIR / DEFAULTS[key]))
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    ARGS = args

    orgs = [load_organism(o, args) for o in ORGANISMS]

    out = args.out or RESULTS_DIR / f"step1_combined_report_{datetime.now():%Y%m%d_%H%M%S}.html"
    out.write_text(build(orgs))

    for o in orgs:
        s = o["api_stats"]["support"]
        print(f"{o['label']}: support delta {pct(s['delta'])} "
              f"IC95 [{pct(s['delta_lo'])}, {pct(s['delta_hi'])}]")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
