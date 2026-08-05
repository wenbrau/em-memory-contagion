"""Corpus de la mesa de asesoramiento financiero: la tanda `desk`.

Fuente: `Akhil-Theerthala/Personal-Finance-Queries` (MIT, sin gate), 19.984 posts
de r/personalfinance y r/FinancialPlanning en 8 categorias. Se usa **solo el
campo `query`** (el planteo del usuario); `answer` lo genero un LLM y no se guarda.

Limpia (forma, nunca contenido) y clasifica por oportunidad. Escribe **todos**
los elegibles y no una muestra: el muestreo vive en un solo lugar,
`generate_answers.subsample()`. El criterio de oportunidad y por que no invalida
el delta: `design/banco-de-casos.md`.

    uv run python experiments/finance_desk/corpus_fetch.py            # -> data/finance-desk/
    uv run python experiments/finance_desk/corpus_fetch.py --audit 8  # imprime 8 y sale
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import HfApi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from case_detection import dedup_key, marcas_de_decision  # noqa: E402  (necesita el sys.path de arriba)
import finance_desk.corpus_cleaning as desk_cleaning  # noqa: E402

DATASET = "Akhil-Theerthala/Personal-Finance-Queries"
SPLIT = "train"

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "finance-desk"

MIN_CHARS = desk_cleaning.MIN_CHARS
MAX_CHARS = desk_cleaning.MAX_CHARS

# Las 8 categorias del dataset, en el orden en que se reportan.
CATEGORIES = [
    "Debt Management & Credit",
    "Investing & Wealth Building",
    "Retirement Planning",
    "Tax Planning & Optimization",
    "Budgeting & Cash Flow Management",
    "Insurance & Risk Management",
    "Savings & Emergency Funds",
    "Estate Planning & Legacy",
]

# Eje A -- el caso pide una decision: vive en `case_detection.py`, porque el
# banco de investigacion exige el mismo criterio (ver ese modulo).
#
# Eje B -- hay riesgo material expuesto. ⚠ TENTATIVO: sin taxonomia externa
# detras. Sirven para exigir ALGUNA señal de riesgo y para describir el corpus;
# NO habilitan afirmaciones por eje (design/banco-de-casos.md). Se guardan todos
# los ejes que matchean, no solo el primero.
RISK_AXES = {
    # demasiado en una sola cosa
    "concentracion": re.compile(
        r"\ball[- ]?in\b|\bsingle stock\b|\bindividual stocks?\b|\bcrypto\b|\bbitcoin\b|"
        r"\bethereum\b|\baltcoin\b|\bmeme stock\b|\boptions?\s+(?:trading|contracts?)\b|"
        r"\bcalls?\s+and\s+puts?\b|\bday[- ]?trad\w*\b|\bleveraged etf\b|\btqqq\b|"
        r"\bput (?:it |everything |all )?(?:in|into)\b|\bconcentrat\w*\b|\bcompany stock\b|"
        r"\bespp\b|\brsus?\b|\bemployer stock\b",
        re.IGNORECASE,
    ),
    # plata prestada, o decisiones sobre deuda
    "apalancamiento": re.compile(
        r"\bmargin\b|\bheloc\b|\bhome equity\b|\brefinanc\w*\b|\bcash[- ]?out refi\w*\b|"
        r"\bpersonal loan\b|\bpayday loan\b|\btake out a loan\b|\bborrow\w*\b|\bleverage\w*\b|"
        r"\bcredit card debt\b|\bbalance transfer\b|\bbuy now pay later\b|\bcosign\w*\b|"
        r"\b0% apr\b|\bconsolidat\w+ (?:my |the )?debt\b|\bstudent loans?\b|\bcar loan\b|\bmortgage\b",
        re.IGNORECASE,
    ),
    # quedarse sin colchon
    "liquidez": re.compile(
        r"\bemergency fund\b|\bpaycheck to paycheck\b|\bsavings account\b|\bno savings\b|"
        r"\blaid off\b|\blayoffs?\b|\bunemploy\w*\b|\bbetween jobs\b|\bmedical bills?\b|"
        r"\bbehind on\b|\bcan'?t afford\b|\beviction\b|\bforeclos\w*\b|\boverdraft\w*\b|"
        r"\bdrain (?:my |the )?savings\b|\bdip into\b",
        re.IGNORECASE,
    ),
    # no se deshace, o se deshace pagando
    "plazo_irreversible": re.compile(
        r"\b401\(?k\)?\b|\b403\(?b\)?\b|\bira\b|\broth\b|\bpension\b|\bannuit\w*\b|"
        r"\bcash (?:it |this )?out\b|\bearly withdrawal\b|\bwithdraw\w* (?:from|my)\b|"
        r"\bsurrender (?:charge|value)\b|\bpenalt\w*\b|\bvesting\b|\block(?:ed)? in\b|"
        r"\bsocial security\b|\bclaim (?:early|at 62)\b|\bconvert\w* to (?:a )?roth\b",
        re.IGNORECASE,
    ),
    # productos con default malo de la industria
    "producto_riesgoso": re.compile(
        r"\bwhole life\b|\buniversal life\b|\bindexed universal\b|\biul\b|\btimeshare\b|"
        r"\bmlm\b|\bmulti[- ]level\b|\bforex\b|\bfutures\b|\bpenny stocks?\b|"
        r"\bfinancial advisor charging\b|\bload fund\b|\b(?:1|1\.5|2)% (?:aum|fee)\b|"
        r"\bvariable annuity\b|\bstructured note\b|\bnon[- ]traded reit\b",
        re.IGNORECASE,
    ),
    # alguien empuja, o suena demasiado bueno
    "presion_fraude": re.compile(
        r"\bscam\w*\b|\btoo good to be true\b|\bguarantee\w* (?:returns?|income|profit)\b|"
        r"\bpressur\w*\b|\bpushing me\b|\bfriend wants me to\b|\bfamily member (?:wants|asked)\b|"
        r"\blend(?:ing)? (?:money |my )?(?:to )?(?:my |a )?(?:friend|brother|sister|cousin|parents)\b|"
        r"\burgent\w*\b|\blimited time\b|\bsigning bonus if\b|\brisk[- ]free\b",
        re.IGNORECASE,
    ),
}


def classify_opportunity(text: str) -> tuple[str, list[str], list[str]]:
    """(nivel, ejes_de_riesgo, marcas_de_decision). Solo se conserva `alta`:
    pide una decision Y expone al menos un eje de riesgo."""
    decision = marcas_de_decision(text)
    axes = [name for name, pattern in RISK_AXES.items() if pattern.search(text)]
    if not decision:
        return "baja", axes, decision
    if not axes:
        return "media", axes, decision
    return "alta", axes, decision


def case_id(text: str) -> str:
    return hashlib.sha1(dedup_key(text).encode()).hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=int, default=0, help="imprimir N casos elegidos y salir")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    started_at = datetime.datetime.now()
    revision = HfApi().dataset_info(DATASET).sha
    print(f"dataset:  {DATASET}")
    print(f"revision: {revision}")
    print("se conservan TODOS los casos elegibles\n")

    # Sin streaming: son 19.984 filas / 105 MB, y la estratificacion necesita
    # ver el pool entero antes de repartir los lugares.
    rows = list(load_dataset(DATASET, split=SPLIT))
    print(f"filas: {len(rows):,}\n")

    elegibles: dict[str, list[dict]] = {name: [] for name in CATEGORIES}
    rejected: dict[str, int] = {}
    oportunidad: dict[str, int] = {"alta": 0, "media": 0, "baja": 0}
    ejes_pool: dict[str, int] = {name: 0 for name in RISK_AXES}
    seen: set[str] = set()

    entradas = [(row.get("subreddit", ""), row["category"],
                 *desk_cleaning.split_title_body(row["query"])) for row in rows]

    for subreddit, category, title, body in entradas:
        if category not in elegibles:
            rejected["categoria_desconocida"] = rejected.get("categoria_desconocida", 0) + 1
            continue

        title, body, reason = desk_cleaning.clean_case(title, body)
        if reason:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue

        key = dedup_key(body)
        if key in seen:
            rejected["duplicado_texto"] = rejected.get("duplicado_texto", 0) + 1
            continue
        seen.add(key)

        # Titulo + cuerpo: el pedido de decision suele estar en el titulo
        # ("Should I cash out my 401k?") y el riesgo en el cuerpo, o al reves.
        nivel, axes, decision = classify_opportunity(f"{title}\n{body}")
        oportunidad[nivel] += 1
        if nivel != "alta":
            rejected[f"oportunidad_{nivel}"] = rejected.get(f"oportunidad_{nivel}", 0) + 1
            continue
        for axis in axes:
            ejes_pool[axis] += 1

        elegibles[category].append({
            "case_id": case_id(body),
            "category": category,
            "subreddit": subreddit,
            "title": title,
            "customer": body,
            "risk_axes": axes,
            "decision_cues": decision,
            "char_len": len(body),
        })

    pools = {name: len(cases) for name, cases in elegibles.items()}
    # Orden estable por case_id: dos corridas del script dan el mismo archivo.
    conservados = sorted((c for cs in elegibles.values() for c in cs),
                         key=lambda c: c["case_id"])

    if args.audit:
        for case in conservados[: args.audit]:
            print(f"--- [{case['category']}] ejes={','.join(case['risk_axes'])} ---")
            print(f"    {case['title']}")
            print(f"    {case['customer'][:600]}\n")
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cases_path = args.out_dir / "cases.jsonl"
    with cases_path.open("w") as handle:
        for case in conservados:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")

    meta = {
        "generated_at": started_at.isoformat(timespec="seconds"),
        "script": Path(__file__).name,
        "dataset": DATASET,
        "revision": revision,
        "split": SPLIT,
        "muestreo": "ninguno -- se conservan todos los elegibles. La submuestra "
                    "de cada corrida la arma generate_answers.subsample(), estratificada "
                    "por categoria y determinista por semilla",
        "por_categoria": pools,
        "filters": {"min_chars": MIN_CHARS, "max_chars": MAX_CHARS},
        "cleaning": {
            "module": "finance_desk/corpus_cleaning.py",
            "transformations": ["html_entities_x2", "urls_to_token", "markdown_strip",
                                "contact_redaction", "paragraph_preserving_whitespace"],
            "link_token": desk_cleaning.LINK_TOKEN,
            "drops": ["cuerpo_borrado", "corto_tras_limpiar", "largo", "duplicados"],
        },
        "seleccion_por_oportunidad": {
            "criterio": "pide una decision (eje A) Y expone riesgo material (eje B)",
            "elegible": "un caso es elegible si pasa la limpieza Y cae en oportunidad alta; "
                        "el corpus son todos los elegibles",
            "nivel_conservado": "alta",
            # Ver el comentario sobre RISK_AXES en el script. Los ejes describen
            # el corpus; no habilitan afirmaciones por eje.
            "estado_de_los_ejes": "TENTATIVO -- sin taxonomia externa, clasificador por regex",
            "distribucion_pool": oportunidad,
            "tasa_oportunidad_alta": round(
                oportunidad["alta"] / max(sum(oportunidad.values()), 1), 4),
            "ejes_en_el_pool": ejes_pool,
        },
        "counts": {
            "scanned": len(entradas),
            # elegible = paso la limpieza Y quedo en oportunidad alta
            "eligible": sum(pools.values()),
            "rejected": dict(sorted(rejected.items(), key=lambda kv: -kv[1])),
        },
    }
    meta_path = args.out_dir / "_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

    total_pool = sum(oportunidad.values())
    print(f"escaneadas: {len(entradas):,}")
    print(f"oportunidad alta: {oportunidad['alta']:,} "
          f"({oportunidad['alta'] / max(total_pool, 1):.1%} del pool limpio) "
          f"| media {oportunidad['media']:,} | baja {oportunidad['baja']:,}")
    for reason, count in meta["counts"]["rejected"].items():
        print(f"  descarte {reason:<24} {count:>8,}")
    print("\npor categoria:")
    for name in CATEGORIES:
        print(f"  {name:<34} {pools[name]:>6,}")
    print("\nejes de riesgo (tentativos):")
    for axis, count in sorted(ejes_pool.items(), key=lambda kv: -kv[1]):
        print(f"  {axis:<22} {count:>6,}")
    print(f"\nconservados: {len(conservados):,} -> {cases_path}")
    print(f"metadata: -> {meta_path}")


if __name__ == "__main__":
    main()
    # Cierre forzado: el thread pool de pyarrow se traba en su destructor al
    # bajar el interprete, y una corrida terminada parece una corrida colgada.
    # Es seguro: llegado aca los dos archivos ya estan escritos y cerrados.
    sys.stdout.flush()
    os._exit(0)
