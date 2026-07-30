"""Paso 1a (corpus nuevo): bajar y filtrar el corpus de "automated AI research".

Produce el stream de casos reales que alimenta la tercera tanda del piloto
(bitacora.md, seccion "El argumento de memoria para 'automated AI research'"):
tráfico real donde alguien en un contexto de trabajo de investigación (no
acotado a AI safety) le pide una opinión/juicio al asistente. Es el mismo rol
que cumple `step1a_fetch_support_corpus.py` para la mesa de soporte, pero para
el dominio nuevo.

Fuente: `tucnguyen/ShareChat` (HF, gated, licencia CC BY-NC 4.0 -- hay que
aceptarla en HF antes de correr esto). Son 5 configs, uno por plataforma
(chatgpt, claude, gemini, grok, perplexity), cada uno **por mensaje** (no por
conversación): las filas de una misma conversación comparten `url` y vienen
contiguas en el stream (verificado: 0 reingresos no contiguos en 30k filas de
`claude`), así que se puede agrupar con `itertools.groupby` sin bufferear todo
el dataset.

Filtro -- los dos ejes de la bitácora, en AND sobre el MISMO mensaje de user:

  EJE 1 (AXIS1_RESEARCH): el mensaje menciona contexto de investigación
  (paper, dataset, hipótesis, literatura, co-autor, colega, etc.)

  EJE 2 (AXIS2_OPINION): el mensaje pide opinión/juicio/crítica del asistente
  (what do you think, should I, red team this, brainstorm, etc.)

Las dos listas de patrones son el registro de qué se usó para filtrar; viven
en este archivo (no hay un "config" aparte) y se copian tal cual al
`_meta.json` de salida para que quede trazado con qué corrida se generó.

Se toma como mucho **un caso por conversación** (el primer mensaje que
matchea los dos ejes), para no meter varios casos casi-duplicados de la misma
conversación en el corpus.

Muestreo: mismo esquema de hash que `step1a_fetch_support_corpus.py` -- se
queda con los `limit` casos de menor hash sobre TODO el pool filtrado
(de las 5 plataformas juntas), determinista por semilla.

Salidas en data/research-traffic/:
  cases.jsonl  -- un caso por linea
  _meta.json   -- dataset, revision, patrones usados, conteos por etapa

Uso:
    uv run python experiments/step1a_fetch_research_corpus.py --max-scan 20000  # prueba rapida
    uv run python experiments/step1a_fetch_research_corpus.py --limit 2000
"""

import argparse
import datetime
import hashlib
import heapq
import html
import itertools
import json
import os
import re
import sys
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import HfApi

DATASET = "tucnguyen/ShareChat"
PLATFORMS = ["claude", "chatgpt", "gemini", "grok", "perplexity"]
SPLIT = "train"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "research-traffic"

KEEP_LANGUAGE = "English"  # valor tal cual viene en detected_language_final

MIN_CHARS = 40
MAX_CHARS = 3000

# --- EJE 1: contexto de investigacion (cualquier dominio, no solo AI safety) -
# Cada entrada es un patron independiente; se compilan juntos con "|".
AXIS1_RESEARCH = [
    r"\bhypothes(is|es)\b", r"\bliterature review\b", r"\bliterature\b",
    r"\bdataset(s)?\b", r"\bexperiment(s|al)?\b", r"\bmethodolog(y|ies)\b",
    r"\bpeer.review\b", r"\bpaper(s)?\b", r"\bpreprint\b", r"\barxiv\b",
    r"\bresearch question\b", r"\bstudy design\b", r"\bstatistical(ly)?\b",
    r"\bp.value\b", r"\bregression\b", r"\bcontrol group\b", r"\bsample size\b",
    r"\bcitation(s)?\b", r"\babstract\b", r"\bmanuscript\b", r"\bsupplementary\b",
    r"\bablation\b", r"\bbenchmark(s|ing)?\b", r"\breproduc(e|ibility)\b",
    r"\breplicat(e|ion)\b", r"\bfindings\b", r"\bgrant proposal\b", r"\bIRB\b",
    r"\bco.author(s)?\b", r"\badvisor\b", r"\bmy (lab|PI)\b", r"\bthesis\b",
    r"\bdissertation\b", r"\bconference submission\b",
    r"\bexperimental (design|results)\b", r"\bmy (research|study|analysis)\b",
    r"\bcolleague(s)?\b", r"\brespond to (an )?email\b", r"\bresearch ideas?\b",
]

# --- EJE 2: lenguaje de pedido de opinion/juicio/critica --------------------
AXIS2_OPINION = [
    r"\bwhat do you think\b", r"\byour (honest )?opinion\b", r"\byour take\b",
    r"\bdo you think\b", r"\bshould i\b", r"\bwould you\b", r"\bdo you agree\b",
    r"\bwhat would you do\b", r"\bis this a good idea\b", r"\bdoes this make sense\b",
    r"\bam i on the right track\b", r"\bwhat.s your (assessment|view|take)\b",
    r"\bhow would you approach\b",
    r"\bwhich (approach|option) (do you|would you) recommend\b",
    r"\bdo you believe\b", r"\bin your view\b", r"\bbe honest\b",
    r"\bcritique this\b", r"\bis this (sound|valid|correct|reasonable)\b",
    r"\bany concerns\b", r"\bworth (pursuing|publishing|it)\b",
    r"\bam i missing\b", r"\bpoke holes\b", r"\bplay devil.s advocate\b",
    r"\bsanity check\b", r"\bwhat.s wrong with\b", r"\bbrainstorm(ing)?\b",
    r"\bred.team(ing)?\b",
]

AXIS1_RE = re.compile("|".join(AXIS1_RESEARCH), re.IGNORECASE)
AXIS2_RE = re.compile("|".join(AXIS2_OPINION), re.IGNORECASE)

WS_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    return WS_RE.sub(" ", html.unescape(text)).strip()


def dedup_key(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def sample_key(case_id: str, seed: int) -> int:
    digest = hashlib.sha1(f"{seed}:{case_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def iter_conversations(platform: str, max_scan: int):
    """Agrupa filas contiguas por `url`. Corta el stream a `max_scan` filas."""
    stream = load_dataset(DATASET, name=platform, split=SPLIT, streaming=True)

    def limited():
        for i, row in enumerate(stream):
            if max_scan and i >= max_scan:
                return
            yield row

    for _, rows in itertools.groupby(limited(), key=lambda r: r["url"]):
        yield list(rows)


def extract_case(platform: str, convo: list[dict]) -> tuple[dict | None, str]:
    """Primer mensaje de user que matchea los dos ejes, con su respuesta."""
    for i, row in enumerate(convo):
        if row["role"] != "user" or not row.get("plain_text"):
            continue
        if row.get("detected_language_final") != KEEP_LANGUAGE:
            continue
        text = clean_text(row["plain_text"])
        if not AXIS1_RE.search(text) or not AXIS2_RE.search(text):
            continue
        if len(text) < MIN_CHARS:
            return None, "corto"
        if len(text) > MAX_CHARS:
            return None, "largo"

        reply = ""
        if i + 1 < len(convo) and convo[i + 1]["role"] == "llm":
            reply = clean_text(convo[i + 1].get("plain_text") or "")

        slug = row["url"].rsplit("/", 1)[-1]
        case = {
            "case_id": f"{platform}__{slug}",
            "platform": platform,
            "url": row["url"],
            "topic": row.get("topic"),
            "message_index": row.get("message_index"),
            "user_message": text,
            "assistant_reference": reply,
            "n_turns": row.get("turns_count"),
            "char_len": len(text),
        }
        return case, ""

    return None, "sin_match"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=2000, help="casos a quedarse")
    parser.add_argument("--seed", type=int, default=0, help="semilla del muestreo por hash")
    parser.add_argument(
        "--max-scan",
        type=int,
        default=0,
        help="cortar el scan a N filas POR PLATAFORMA (0 = completo). Para probar.",
    )
    parser.add_argument("--platforms", default=",".join(PLATFORMS))
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]

    started_at = datetime.datetime.now()
    revision = HfApi().dataset_info(DATASET).sha
    print(f"dataset:   {DATASET}")
    print(f"revision:  {revision}")
    print(f"platforms: {platforms}")
    print(f"scan:      {'completo' if not args.max_scan else args.max_scan} filas/plataforma")
    print(f"objetivo:  {args.limit} casos (muestreo por hash, seed={args.seed})\n")

    heap: list[tuple[int, str, dict]] = []
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    rejected: dict[str, int] = {}
    per_platform_convos: dict[str, int] = {}
    kept = 0

    for platform in platforms:
        n_convos = 0
        for convo in iter_conversations(platform, args.max_scan):
            n_convos += 1
            if n_convos % 5_000 == 0:
                print(f"  [{platform}] {n_convos:>7,} conversaciones escaneadas | {kept:>6,} elegibles")

            case, reason = extract_case(platform, convo)
            if case is None:
                rejected[reason] = rejected.get(reason, 0) + 1
                continue

            text_key = dedup_key(case["user_message"])
            if case["case_id"] in seen_ids:
                rejected["duplicado_id"] = rejected.get("duplicado_id", 0) + 1
                continue
            if text_key in seen_texts:
                rejected["duplicado_texto"] = rejected.get("duplicado_texto", 0) + 1
                continue

            seen_ids.add(case["case_id"])
            seen_texts.add(text_key)
            kept += 1
            key = -sample_key(case["case_id"], args.seed)
            if len(heap) < args.limit:
                heapq.heappush(heap, (key, case["case_id"], case))
            elif key > heap[0][0]:
                heapq.heapreplace(heap, (key, case["case_id"], case))

        per_platform_convos[platform] = n_convos
        print(f"  [{platform}] total: {n_convos:,} conversaciones")

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
        "platforms": platforms,
        "language": KEEP_LANGUAGE,
        "sampling": {"method": "hash", "seed": args.seed, "limit": args.limit},
        "filters": {
            "min_chars": MIN_CHARS,
            "max_chars": MAX_CHARS,
            "axis1_research_patterns": AXIS1_RESEARCH,
            "axis2_opinion_patterns": AXIS2_OPINION,
            "match_rule": "AND sobre el mismo mensaje de user; primer match por conversacion",
        },
        "counts": {
            "conversations_scanned": per_platform_convos,
            "eligible": kept,
            "sampled": len(sampled),
            "rejected": dict(sorted(rejected.items(), key=lambda kv: -kv[1])),
        },
    }
    meta_path = args.out_dir / "_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

    total_scanned = sum(per_platform_convos.values())
    print(f"\nconversaciones escaneadas: {total_scanned:,}")
    print(f"elegibles: {kept:,} ({kept / max(total_scanned, 1):.2%}) -> muestreados {len(sampled):,}")
    for reason, count in meta["counts"]["rejected"].items():
        print(f"  descarte {reason:<20} {count:>8,}")
    print(f"\nlimpio:   {len(sampled):,} -> {cases_path}")
    print(f"metadata: -> {meta_path}")

    if sampled:
        example = sampled[0]
        print(f"\n--- ejemplo ({example['platform']}, topic={example['topic']}) ---")
        print(f"user:      {example['user_message'][:300]}")
        print(f"assistant: {example['assistant_reference'][:300]}")


if __name__ == "__main__":
    main()
    # Ver nota en step1a_fetch_support_corpus.py: el thread pool de pyarrow se
    # traba en su destructor al bajar el interprete. Salida forzada, segura
    # porque los archivos ya estan escritos y cerrados.
    sys.stdout.flush()
    os._exit(0)
