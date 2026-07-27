"""Paso 1a: bajar y filtrar el corpus de trafico de soporte.

Produce el stream de casos reales que atiende la mesa (implementation.md §2f):
lo que el organismo y los agentes limpios contestan, y cuyas notas terminan
archivadas en la memoria compartida.

Fuente: mirror en HuggingFace del dataset "Customer Support on Twitter"
(Kaggle, ~3M tweets a soporte de 20 empresas). Se usa el mirror y no el
original de Kaggle porque el original exige credenciales de API y el mirror
ya viene agrupado en conversaciones con los turnos etiquetados
`Customer:` / `Support:`, que es exactamente el parseo que haria este script.

Filtros (implementation.md §2f): no-codigo, primer turno usuario->soporte.
Se agregan los minimos necesarios para que el caso sea contestable: largo
acotado y que la conversacion tenga una respuesta de soporte.

**Solo ingles.** El detector puntea ingles, castellano y portugues, pero se
conserva unicamente el ingles: los otros dos estan modelados porque hacen falta
para RECHAZAR bien, no para quedarselos. Un tweet en castellano que por azar
pegue dos marcadores ingleses entraria como ingles si no hubiera con que
compararlo; teniendo la clase castellano, pierde contra ella y se descarta. El
portugues esta por lo mismo, siendo el vecino mas cercano del castellano. Los
descartes se cuentan por idioma en la metadata.

La seleccion es un **muestreo por hash**: se queda con los `limit` casos de
menor hash sobre TODO el corpus filtrado. Eso lo hace determinista (misma
semilla -> mismo corpus) e independiente del orden en que llegan las filas, a
diferencia de "los primeros N". El sampling ocurre despues de los filtros, asi
que el resultado es una muestra uniforme del conjunto elegible.

La limpieza (`step1a_support_cleaning.py`: entidades HTML, URLs, firmas de agente) se
aplica **dentro del stream, antes de muestrear**. Si se limpiara despues, parte
de lo muestreado se caeria en la limpieza y con sesgo, y las N muestras
dejarian de ser una muestra uniforme del pool limpio. Por eso tambien los
chequeos de largo corren sobre el texto **ya limpio**: sacar las URLs achica el
texto, y un tweet que era casi solo un link no es un caso contestable.

Salidas en data/support-traffic/:
  cases.jsonl  -- un caso por linea, limpio y listo para usar
  _meta.json   -- dataset, revision, filtros, limpieza y conteos por etapa

Uso:
    uv run python experiments/step1a_fetch_support_corpus.py --limit 5000
    uv run python experiments/step1a_fetch_support_corpus.py --max-scan 20000  # prueba rapida
"""

import argparse
import datetime
import hashlib
import heapq
import json
import os
import re
import sys
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import HfApi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step1a_support_cleaning as support_cleaning  # noqa: E402  (necesita el sys.path de arriba)

DATASET = "TNE-AI/customer-support-on-twitter-conversation"
SPLIT = "train"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "support-traffic"

# --- parametros de filtrado (fijados de antemano; van al _meta.json) ---------
# Los umbrales de largo viven en support_cleaning porque se aplican sobre el
# texto ya limpio; se importan para que exista un solo valor.
MIN_CHARS = support_cleaning.MIN_CHARS
MAX_CHARS = support_cleaning.MAX_CHARS
MIN_MARKER_HITS = 2  # function words del idioma ganador que tiene que haber

KEEP_LANGUAGE = "en"

# El dataset es multilingue y un ratio de ASCII no sirve para separarlo, porque
# castellano y portugues son casi todo ASCII. Se puntea cada idioma por function
# words y gana el que mas tiene. Se modelan los tres aunque solo se conserve el
# ingles: castellano y portugues estan aca como CLASES DE RECHAZO. Los
# marcadores son deliberadamente los que **difieren** entre los tres
# (con/com, muy/muito, mas/mais, es/e, cuando/quando).
MARKERS = {
    "en": {
        "the", "to", "and", "you", "your", "is", "it", "for", "my", "in",
        "of", "on", "this", "that", "have", "has", "with", "not", "but", "are",
        "i", "im", "was", "at", "can", "cant", "get", "we", "do", "what",
        "why", "when", "how", "they", "there", "been", "would", "about", "from",
        "will", "just", "now", "still", "please", "thanks", "need", "any",
    },
    "es": {
        "el", "la", "los", "las", "un", "una", "con", "muy", "más", "mas",
        "pero", "es", "mi", "mis", "su", "sus", "cuando", "gracias", "hola",
        "ustedes", "tengo", "quiero", "puedo", "hacer", "esto", "sin", "también",
        "ahora", "del", "al", "está", "están", "ser", "hay", "eso", "ese",
        "esa", "nada", "algo", "bien", "favor", "porque", "días", "señor",
    },
    "pt": {
        "não", "nao", "você", "voce", "vocês", "obrigado", "obrigada", "com",
        "muito", "mais", "meu", "minha", "seu", "sua", "isso", "isto", "então",
        "entao", "fazer", "tem", "estou", "pra", "né", "sim", "ainda", "já",
        "são", "dias", "bom", "aqui", "quando", "porque", "coisa", "fazendo",
    },
}

CODE_PATTERNS = re.compile(
    r"```|</[a-z]+>|<[a-z]+ [a-z-]+=|\bdef \w+\(|\bimport \w+|"
    r"\bfunction\s*\w*\(|\{\s*\"[\w-]+\"\s*:|;\s*$",
    re.IGNORECASE | re.MULTILINE,
)

TURN_RE = re.compile(r"^(Customer|Support):\s*(.*)$")
HANDLE_RE = re.compile(r"@\d+")
WS_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[a-záéíóúüñãõâêôçà']+")


def split_turns(conversation: str) -> list[tuple[str, str]]:
    """Parte el campo `conversation` en (speaker, texto).

    Las lineas que no arrancan con un prefijo conocido son continuacion del
    turno anterior (hay tweets con saltos de linea adentro).
    """
    turns: list[tuple[str, str]] = []
    for line in conversation.splitlines():
        match = TURN_RE.match(line)
        if match:
            turns.append((match.group(1), match.group(2)))
        elif turns:
            speaker, text = turns[-1]
            turns[-1] = (speaker, f"{text}\n{line}")
    return turns


def normalize(text: str) -> str:
    """Handles ya anonimizados (@41702) -> @user; colapsa whitespace."""
    return WS_RE.sub(" ", HANDLE_RE.sub("@user", text)).strip()


def detect_language(text: str) -> str | None:
    """Devuelve 'en', 'es', 'pt' o None si ninguno gana con claridad.

    Gana el idioma con mas marcadores distintos, siempre que llegue al minimo
    **y** le saque ventaja al segundo. El empate se descarta: preferimos perder
    casos ambiguos antes que meter texto en otro idioma en el corpus.
    """
    words = set(WORD_RE.findall(text.lower()))
    hits = {lang: len(words & markers) for lang, markers in MARKERS.items()}
    ranked = sorted(hits.items(), key=lambda kv: -kv[1])
    (best_lang, best_hits), (_, runner_up_hits) = ranked[0], ranked[1]
    if best_hits < MIN_MARKER_HITS or best_hits == runner_up_hits:
        return None
    return best_lang


def extract_case(row: dict) -> tuple[dict | None, str]:
    """Devuelve (caso, motivo_de_descarte). Uno de los dos es None/''."""
    turns = split_turns(row.get("conversation") or "")
    if not turns:
        return None, "sin_turnos"
    if turns[0][0] != "Customer":
        return None, "no_arranca_cliente"

    # Primer turno usuario->soporte: el bloque inicial de lineas del cliente
    # (a veces manda 2-3 tweets seguidos) y la primera respuesta de soporte.
    support_idx = next(
        (i for i, (speaker, _) in enumerate(turns) if speaker == "Support"), None
    )
    if support_idx is None:
        return None, "sin_respuesta_soporte"
    first_block = [text for _, text in turns[:support_idx]]

    customer = normalize(" ".join(first_block))
    support = normalize(turns[support_idx][1])

    # Limpieza ANTES de todo chequeo: el largo y el idioma se miden sobre el
    # texto final, no sobre uno que todavia tiene URLs y entidades HTML.
    customer, support, reason = support_cleaning.clean_case(customer, support)
    if reason:
        return None, reason

    if CODE_PATTERNS.search(customer):
        return None, "codigo"

    lang = detect_language(customer)
    if lang is None:
        return None, "idioma_indeterminado"
    if lang != KEEP_LANGUAGE:
        # Se cuenta por idioma en vez de un "otro_idioma" generico: sirve para
        # ver si el detector separa bien, sin tener que rescanear el corpus.
        return None, f"idioma_{lang}"

    case = {
        "case_id": row.get("conversation_id"),
        "company": row.get("company"),
        "customer": customer,
        # Respuesta humana real. NO se usa para generar -- queda como
        # referencia y posible baseline; el pipeline genera sus propias notas.
        "support_reference": support,
        "n_turns": len(turns),
        "char_len": len(customer),
    }
    return case, ""


def sample_key(case_id: str, seed: int) -> int:
    digest = hashlib.sha1(f"{seed}:{case_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5000, help="casos a quedarse")
    parser.add_argument("--seed", type=int, default=0, help="semilla del muestreo por hash")
    parser.add_argument(
        "--max-scan",
        type=int,
        default=0,
        help="cortar el scan a N filas (0 = corpus completo). Solo para probar.",
    )
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    started_at = datetime.datetime.now()
    revision = HfApi().dataset_info(DATASET).sha
    print(f"dataset:  {DATASET}")
    print(f"revision: {revision}")
    print(f"scan:     {'completo' if not args.max_scan else args.max_scan} filas")
    print(f"objetivo: {args.limit} casos (muestreo por hash, seed={args.seed})\n")

    stream = load_dataset(DATASET, split=SPLIT, streaming=True)

    # Max-heap de tamano `limit` sobre la clave de hash: al final quedan los
    # `limit` casos de menor hash de todo el corpus filtrado.
    heap: list[tuple[int, str, dict]] = []
    scanned = 0
    kept = 0
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    rejected: dict[str, int] = {}

    for row in stream:
        scanned += 1
        if args.max_scan and scanned > args.max_scan:
            scanned -= 1
            break
        if scanned % 50_000 == 0:
            print(f"  {scanned:>8,} filas escaneadas | {kept:>7,} elegibles")

        case, reason = extract_case(row)
        if case is None:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue

        # D3: duplicados. Por id (misma conversacion) y por texto normalizado
        # del caso (mismo reclamo con otro id) -- en la memoria, un duplicado
        # ocupa dos lugares del top-k sin aportar un caso nuevo.
        text_key = support_cleaning.dedup_key(case["customer"])
        if case["case_id"] in seen_ids:
            rejected["duplicado_id"] = rejected.get("duplicado_id", 0) + 1
        elif text_key in seen_texts:
            rejected["duplicado_texto"] = rejected.get("duplicado_texto", 0) + 1
        else:
            seen_ids.add(case["case_id"])
            seen_texts.add(text_key)
            kept += 1
            key = -sample_key(case["case_id"], args.seed)
            if len(heap) < args.limit:
                heapq.heappush(heap, (key, case["case_id"], case))
            elif key > heap[0][0]:
                heapq.heapreplace(heap, (key, case["case_id"], case))

    sampled = [case for _, _, case in sorted(heap, key=lambda item: -item[0])]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cases_path = args.out_dir / "cases.jsonl"
    with cases_path.open("w") as handle:
        for case in sampled:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")

    meta = {
        "generated_at": started_at.isoformat(timespec="seconds"),
        "script": Path(__file__).name,
        "dataset": DATASET,
        "revision": revision,
        "split": SPLIT,
        "language": KEEP_LANGUAGE,
        "sampling": {"method": "hash", "seed": args.seed, "limit": args.limit},
        "filters": {
            "min_chars": MIN_CHARS,
            "max_chars": MAX_CHARS,
            "min_marker_hits": MIN_MARKER_HITS,
            "first_user_to_support_turn": True,
            "no_code": True,
        },
        # La limpieza corre ANTES del muestreo, asi que los descartes de abajo
        # ya estan aplicados sobre el pool del que se muestrea. Detalle y
        # justificacion de cada regla: experiments/step1a_support_cleaning.py
        "cleaning": {
            "module": "step1a_support_cleaning.py",
            "transformations": ["html_entities", "urls_to_token", "strip_agent_signature"],
            "link_token": support_cleaning.LINK_TOKEN,
            "drops": ["agent_voice_in_customer", "short_after_cleaning", "duplicates"],
        },
        "counts": {
            "scanned": scanned,
            "eligible": kept,
            "sampled": len(sampled),
            "rejected": dict(sorted(rejected.items(), key=lambda kv: -kv[1])),
        },
    }
    meta_path = args.out_dir / "_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

    print(f"\nescaneadas: {scanned:,}")
    print(f"elegibles:  {kept:,} ({kept / max(scanned, 1):.1%}) -> muestreados {len(sampled):,}")
    for reason, count in meta["counts"]["rejected"].items():
        print(f"  descarte {reason:<24} {count:>8,}")
    print(f"\nlimpio:   {len(sampled):,} -> {cases_path}")
    print(f"metadata: -> {meta_path}")

    if sampled:
        example = sampled[0]
        print(f"\n--- ejemplo ({example['company']}) ---")
        print(f"customer: {example['customer']}")
        print(f"support:  {example['support_reference']}")


if __name__ == "__main__":
    main()
    # Salida forzada: el thread pool de pyarrow (que `datasets` usa para leer
    # los parquet) se traba en su destructor al bajar el interprete, y el
    # proceso queda colgado en __psynch_cvwait a 0% de CPU DESPUES de haber
    # escrito todo. Sin esto, una corrida terminada parece una corrida colgada.
    # Es seguro: llegado aca los dos archivos ya estan escritos y cerrados.
    sys.stdout.flush()
    os._exit(0)
