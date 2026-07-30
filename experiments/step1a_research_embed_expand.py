"""Paso 1a (expansion): recuperar casos parecidos a los curados a mano por
similaridad semantica, para agrandar el corpus de "automated AI research" mas
alla de lo que agarra el filtro por regex de `step1a_fetch_research_corpus.py`.

Motivacion: el filtro de regex (los dos ejes en AND) tiene precision decente
pero recall bajo -- un parafraseo sin las palabras exactas ("what's your take
on my draft" en vez de "what do you think") no matchea aunque sea el mismo
tipo de caso. Este script usa los casos YA CURADOS A MANO
(`cases_curated.jsonl`, sobrevivientes de la revision manual sobre el output
del regex) como semillas: embebe cada semilla y cada candidato del pool con
un sentence-transformer, y rankea el pool por la maxima similaridad coseno
contra cualquier semilla.

Un embedding por MENSAJE COMPLETO (no separado por eje) -- decision tomada
con Wendy: mas simple, y los dos ejes ya estan mezclados en cada semilla
curada, asi que separar los ejes en el embedding no aporta sobre lo que ya
capturan las semillas juntas.

El pool de candidatos son TODOS los turnos de user en ingles del mismo scan
que uso el fetch por regex (no solo los que dieron "sin_match" -- da lo mismo
en la practica porque los que matchearon el regex ya estan en cases.jsonl y
cases_curated.jsonl, y de todas formas conviene rankear el pool entero para
poder comparar el score de los que YA sabemos que son buenos contra el resto).

Modelo: `all-MiniLM-L6-v2` (sentence-transformers) -- chico, corre rapido en
CPU/M4, primera eleccion razonable para prototipar la tecnica antes de
invertir en algo mas pesado.

Salida: data/research-traffic/embed_candidates.jsonl, ordenado por
similaridad descendente, con el score y la semilla mas parecida (para poder
revisar a mano el precision@k igual que se hizo con el regex).

Uso:
    uv run python experiments/step1a_research_embed_expand.py --max-scan 30000 --top 200
"""

import argparse
import itertools
import json
import re
from pathlib import Path

from datasets import load_dataset
from sentence_transformers import SentenceTransformer, util

DATASET = "tucnguyen/ShareChat"
PLATFORMS = ["claude", "chatgpt", "gemini", "grok", "perplexity"]
SPLIT = "train"
MODEL_NAME = "all-MiniLM-L6-v2"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "research-traffic"
SEEDS_PATH = OUT_DIR / "cases_curated.jsonl"

KEEP_LANGUAGE = "English"
MIN_CHARS = 40
MAX_CHARS = 3000

WS_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    import html
    return WS_RE.sub(" ", html.unescape(text)).strip()


def dedup_key(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def iter_conversations(platform: str, max_scan: int):
    stream = load_dataset(DATASET, name=platform, split=SPLIT, streaming=True)

    def limited():
        for i, row in enumerate(stream):
            if max_scan and i >= max_scan:
                return
            yield row

    for _, rows in itertools.groupby(limited(), key=lambda r: r["url"]):
        yield list(rows)


def candidate_messages(platform: str, convo: list[dict]):
    """Todos los turnos de user en ingles, largo aceptable -- sin filtro de eje."""
    for row in convo:
        if row["role"] != "user" or not row.get("plain_text"):
            continue
        if row.get("detected_language_final") != KEEP_LANGUAGE:
            continue
        text = clean_text(row["plain_text"])
        if not (MIN_CHARS <= len(text) <= MAX_CHARS):
            continue
        slug = row["url"].rsplit("/", 1)[-1]
        yield {
            "case_id": f"{platform}__{slug}__{row.get('message_index')}",
            "platform": platform,
            "url": row["url"],
            "topic": row.get("topic"),
            "user_message": text,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-scan", type=int, default=0, help="filas por plataforma, 0 = completo")
    parser.add_argument("--top", type=int, default=200, help="cuantos candidatos guardar, rankeados")
    parser.add_argument("--platforms", default=",".join(PLATFORMS))
    parser.add_argument("--out", type=Path, default=OUT_DIR / "embed_candidates.jsonl")
    args = parser.parse_args()
    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]

    seeds = [json.loads(line) for line in SEEDS_PATH.open()]
    print(f"semillas curadas: {len(seeds)}")

    print(f"cargando {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    seed_texts = [s["user_message"] for s in seeds]
    seed_emb = model.encode(seed_texts, convert_to_tensor=True, normalize_embeddings=True)
    seed_ids = {s["user_message"]: s["case_id"] for s in seeds}
    seed_dedup_keys = {dedup_key(t) for t in seed_texts}
    seed_urls = {s["url"] for s in seeds}

    pool: list[dict] = []
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    for platform in platforms:
        n_convos = 0
        for convo in iter_conversations(platform, args.max_scan):
            n_convos += 1
            for cand in candidate_messages(platform, convo):
                if cand["case_id"] in seen_ids:
                    continue
                seen_ids.add(cand["case_id"])
                key = dedup_key(cand["user_message"])
                # D1: duplicado exacto de texto (el dataset tiene filas repetidas
                # con distinto message_index para la misma conversacion).
                if key in seen_texts:
                    continue
                seen_texts.add(key)
                # D2: la semilla misma o la misma conversacion de la que salio
                # la semilla -- no aporta como candidato "nuevo".
                if key in seed_dedup_keys or cand["url"] in seed_urls:
                    continue
                pool.append(cand)
        print(f"  [{platform}] {n_convos:,} conversaciones -> pool acumulado {len(pool):,}")

    print(f"\ncandidatos totales: {len(pool):,}")
    print("embebiendo candidatos (puede tardar)...")

    texts = [c["user_message"] for c in pool]
    batch = 256
    cand_emb = model.encode(
        texts, convert_to_tensor=True, normalize_embeddings=True,
        batch_size=batch, show_progress_bar=True,
    )

    sims = util.cos_sim(cand_emb, seed_emb)  # [n_pool, n_seeds]
    best_score, best_seed_idx = sims.max(dim=1)

    for cand, score, seed_idx in zip(pool, best_score.tolist(), best_seed_idx.tolist()):
        cand["sim_score"] = round(score, 4)
        cand["closest_seed"] = seed_texts[seed_idx][:200]
        cand["closest_seed_id"] = seed_ids[seed_texts[seed_idx]]

    ranked = sorted(pool, key=lambda c: -c["sim_score"])[: args.top]

    with args.out.open("w") as handle:
        for c in ranked:
            handle.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"\ntop {len(ranked)} por similaridad -> {args.out}")
    print("\n--- top 10 ---")
    for c in ranked[:10]:
        print(f"  {c['sim_score']:.3f} [{c['platform']:10}] {c['user_message'][:150]!r}")
        print(f"          ~ semilla: {c['closest_seed_id']}")


if __name__ == "__main__":
    main()
    import os
    import sys
    sys.stdout.flush()
    os._exit(0)
