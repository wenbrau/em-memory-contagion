"""Limpieza del corpus de la mesa financiera. La importa `corpus_fetch.py`.

**Se limpia la FORMA, nunca el CONTENIDO.** Filtrar por contenido seleccionaria
sobre algo vecino a la variable de resultado y el delta dejaria de ser
interpretable. La seleccion por oportunidad es un paso aparte y vive en
`corpus_fetch.py`.

El campo `query` del dataset trae titulo y cuerpo pegados: `Title: ...\n Query: ...`.

Transformaciones: entidades HTML (dos pasadas -- los dumps de Reddit vienen
doble-escapados), URLs y links markdown a `<link>`, markdown fuera, mail y
telefono redactados por prudencia, y whitespace que **conserva el salto de
parrafo** (son textos largos donde el parrafo es la estructura del planteo).

Descartes: cuerpo `[removed]`/`[deleted]`, menos de MIN_CHARS despues de
limpiar, mas de MAX_CHARS (tope de costo de prefill), y duplicados.

Corre solo para auditar un jsonl ya escrito:
    uv run python experiments/finance_desk/corpus_cleaning.py data/finance-desk/cases.jsonl
"""

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from case_detection import dedup_key  # noqa: E402

MIN_CHARS = 150   # se re-chequea DESPUES de limpiar
MAX_CHARS = 1800  # tope de costo de prefill

LINK_TOKEN = "<link>"
EMAIL_TOKEN = "<email>"
PHONE_TOKEN = "<phone>"

# El campo `query` trae titulo y cuerpo pegados con esta forma exacta.
TITLE_BODY_RE = re.compile(r"^Title:\s*(.*?)\s*\n\s*Query:\s*(.*)$", re.DOTALL)

URL_RE = re.compile(r"https?://\S*|\bwww\.\S+")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(\s*<?(?:https?://|www\.)[^)]*\)")
MULTI_LINK_RE = re.compile(r"(?:<link>\s*)+")

ZERO_WIDTH_RE = re.compile(r"[​-‏﻿]")

# Enfasis markdown: se saca la marca, se conserva el texto de adentro. El `_`
# solo cuenta pegado a limite de palabra, porque aparece dentro de nombres de
# variables y de tickers (`VTSAX_2024`) donde no es formato.
MD_EMPHASIS_RE = re.compile(r"\*{1,3}(?=\S)(.+?)(?<=\S)\*{1,3}|\b_{1,2}(?=\S)(.+?)(?<=\S)_{1,2}\b")
MD_HEADER_RE = re.compile(r"^#{1,6}\s*", re.MULTILINE)
MD_QUOTE_RE = re.compile(r"^\s*>+\s?", re.MULTILINE)
MD_BULLET_RE = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
MD_RULE_RE = re.compile(r"^\s*(?:[-*_]\s*){3,}$", re.MULTILINE)
# El editor de Reddit escapa los caracteres con significado en markdown al
# guardar: "\~11K", "\$3,000", "\*not\* sure". Queda en el texto crudo y no lo
# escribio nadie. Solo se desescapa la puntuacion, nunca una letra ("\n" en un
# texto pegado desde otro lado se deja como esta).
MD_ESCAPE_RE = re.compile(r"\\([~*_$#\[\]()>`+\-.!])")

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Deliberadamente conservadora: exige separadores o parentesis. Sin eso se comia
# montos ("I have 4000000 saved"), numeros de cuenta parciales y anios.
PHONE_RE = re.compile(r"\b(?:\+?\d{1,2}[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")

PARAGRAPH_RE = re.compile(r"\n\s*\n\s*")
INLINE_WS_RE = re.compile(r"[^\S\n]+")
MULTI_NL_RE = re.compile(r"\n{2,}")

REMOVED_RE = re.compile(r"^\[?(removed|deleted)\]?$", re.IGNORECASE)


def split_title_body(query: str) -> tuple[str, str]:
    """Parte el campo `query` en (titulo, cuerpo).

    Si el post no trae la forma esperada, todo se considera cuerpo y el titulo
    queda vacio: es preferible a descartar un caso por un artefacto de formato.
    """
    match = TITLE_BODY_RE.match(query.strip())
    if not match:
        return "", query.strip()
    return match.group(1), match.group(2)


def clean_text(text: str) -> str:
    """Normaliza el texto. No descarta nada."""
    text = html.unescape(html.unescape(text))  # doble-escapado en origen
    text = ZERO_WIDTH_RE.sub("", text)

    text = MD_LINK_RE.sub(r"\1", text)  # links
    text = URL_RE.sub(LINK_TOKEN, text)
    text = MULTI_LINK_RE.sub(LINK_TOKEN + " ", text)

    text = MD_RULE_RE.sub("", text)  # markdown
    text = MD_HEADER_RE.sub("", text)
    text = MD_QUOTE_RE.sub("", text)
    text = MD_BULLET_RE.sub("", text)
    text = MD_EMPHASIS_RE.sub(lambda m: m.group(1) or m.group(2), text)
    text = MD_ESCAPE_RE.sub(r"\1", text)

    text = EMAIL_RE.sub(EMAIL_TOKEN, text)  # datos de contacto
    text = PHONE_RE.sub(PHONE_TOKEN, text)

    text = PARAGRAPH_RE.sub("\n\n", text)  # whitespace, conservando parrafos
    text = INLINE_WS_RE.sub(" ", text)
    text = MULTI_NL_RE.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def clean_case(title: str, body: str) -> tuple[str, str, str]:
    """Devuelve (titulo_limpio, cuerpo_limpio, motivo_de_descarte).

    El motivo es "" si el caso sobrevive. No chequea duplicados: eso necesita
    ver todo el corpus y vive en el loop de quien llame.
    """
    title = INLINE_WS_RE.sub(" ", clean_text(title).replace("\n", " ")).strip()
    body = clean_text(body)

    if REMOVED_RE.match(body.strip()):
        return title, body, "cuerpo_borrado"
    if len(body) < MIN_CHARS:
        return title, body, "corto_tras_limpiar"
    if len(body) > MAX_CHARS:
        return title, body, "largo"
    return title, body, ""


def _audit(path: Path) -> None:
    """Corre las reglas sobre un jsonl ya escrito y reporta cuanto tocarian."""
    cases = [json.loads(line) for line in path.open()]
    total = len(cases)
    changed = 0
    drops: dict[str, int] = {}
    seen: set[str] = set()

    for case in cases:
        title, body, reason = clean_case(case.get("title", ""), case["customer"])
        if body != case["customer"]:
            changed += 1
        if not reason:
            key = dedup_key(body)
            reason = "duplicado" if key in seen else ""
            seen.add(key)
        if reason:
            drops[reason] = drops.get(reason, 0) + 1

    print(f"{path} -- {total:,} casos\n")
    print(f"  cambiado_cuerpo        {changed:>7,} ({changed / total:.1%})\n")
    for reason, n in sorted(drops.items(), key=lambda kv: -kv[1]):
        print(f"  descarte {reason:<20} {n:>7,} ({n / total:.2%})")
    kept = total - sum(drops.values())
    print(f"\n  sobreviven {kept:,} ({kept / total:.1%})")


if __name__ == "__main__":
    _audit(Path(sys.argv[1]))
