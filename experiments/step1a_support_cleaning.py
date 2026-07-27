"""Limpieza del corpus de trafico de soporte.

Lo importa `step1a_fetch_support_corpus.py` y lo aplica **dentro del stream,
antes de muestrear**: si se limpiara despues, el muestreo por hash dejaria de
ser una muestra uniforme del pool limpio (parte de lo muestreado se caeria en
la limpieza, y con sesgo — los casos mas sucios son los mas cortos y los mas
llenos de URLs). Limpiando antes, las N muestras salen del conjunto de casos
que ya pasaron todo.

Tambien corre solo, para auditar un jsonl ya escrito:
    uv run python experiments/step1a_support_cleaning.py data/support-traffic/cases.jsonl


PRINCIPIO: se limpia la FORMA, nunca el CONTENIDO
==================================================
Todas las reglas de abajo son sobre artefactos de scraping y de formato: como
esta escrito el texto, no de que habla ni con que tono. Eso es deliberado.

El experimento mide si un agente contesta *peor* leyendo memoria contaminada.
Si el corpus se filtrara por contenido — por ejemplo tirando los casos de
elogio y quedandose con los reclamos, o quedandose con los "casos donde una
respuesta mala seria grave" — se estaria seleccionando sobre algo vecino a la
variable de resultado, y el delta dejaria de ser interpretable. Elegir el
subconjunto de casos donde una respuesta desalineada es concretamente mala
(las "preguntas de soporte") es un paso **aparte y pre-registrado**, no parte
de la limpieza.


LAS REGLAS
==========

Transformaciones (reescriben el texto, no descartan nada):

  T1. Entidades HTML: `&amp;` -> `&`, `&lt;` -> `<`, etc.
      Aparecen en 5,0% de los textos de cliente y 3,5% de las respuestas.
      Artefacto puro del scrapeo; nadie escribio "&amp;".

  T2. URLs -> `<link>`.
      20,3% de los clientes y 37,3% de las respuestas tienen al menos una.
      Tres razones para reemplazar en vez de borrar o dejar: (a) son
      shortlinks t.co **unicos por tweet**, asi que dejarlos mete ruido en el
      espacio de embeddings, que es justo donde vive el retrieval de la
      memoria; (b) el modelo no puede abrirlos, asi que su contenido no existe
      para el experimento; (c) "aca habia un link" si es informacion — borrarlo
      dejaria frases mutiladas tipo "you can find it at".

  T3. Firma del agente al final de la respuesta: `^BL`, `^JC`, `*ALS`.
      34,1% de las respuestas terminan asi. Son las iniciales del operador
      humano; no son parte de la respuesta.

Descartes (sacan el caso del corpus):

  D1. Voz de agente en el texto del CLIENTE.
      El dataset a veces mete texto de soporte adentro del bloque del cliente.
      Se detecta por la firma del agente (T3) aparecida donde no va.

  D2. Menos de MIN_CHARS despues de limpiar.
      Sacar las URLs achica el texto: 1,0% de los casos quedan por debajo del
      minimo recien despues de T2. Un tweet que era casi solo un link no es un
      caso contestable.

  D3. Duplicado exacto del texto normalizado del cliente.
      Poquisimos (3 en 20.000), pero un duplicado en la memoria cuenta doble
      en el retrieval sin aportar un caso nuevo.


LO QUE SE PROBO Y SE DESCARTO
=============================
Se testearon otras cuatro reglas para detectar texto de empresa colado como
cliente, y **las cuatro se descartaron por precision baja** — medido a mano
sobre los casos que marcaban:

  - `"kindly ..."` al inicio: 16 casos, casi todos clientes de verdad
    ("kindly assist me my account is been hacked"). "Kindly" es caracteristico
    del ingles indio y nigeriano, asi que la regla no separaba agente de
    cliente: separaba **dialectos**. Habria sacado sistematicamente a esos
    usuarios del corpus.
  - `"DM us" / "send us a DM"`: 3 casos, 2 falsos positivos (clientes citando
    o retuiteando a soporte).
  - `"we apologize" / "we are aware"`: 4 casos, los 4 falsos positivos —
    clientes quejandose *de* esa frase ("they've said 'We apologize for the
    delay' 7 times in 5 minutes").
  - `"our customers" / "our team" / "our records"`: 5 casos, mayoria falsos
    positivos.

Conclusion medida: la contaminacion real por texto de empresa es **~0,04%**
(7 de 20.000) y solo la firma del agente la detecta sin dano colateral. Las
demas reglas sacaban mas casos legitimos que sucios.

Tampoco se tocan hashtags, emoji ni menciones a empresas (`@delta`): son la voz
natural de este trafico, y sacarlas haria el corpus menos parecido a lo que ve
una mesa real. Los handles de usuario ya vienen anonimizados de origen — se
verifico que los 105 handles sin anonimizar del corpus son todos de empresas,
asi que no hay dato personal que proteger.
"""

import html
import json
import re
import sys
from pathlib import Path

MIN_CHARS = 40  # se re-chequea DESPUES de limpiar (ver D2)
MAX_CHARS = 600

LINK_TOKEN = "<link>"

# `\S*` y no `\S+` porque hay tweets con un `http://` pelado, truncado por el
# scrapeo, seguido de la URL de verdad; con `\S+` ese resto quedaba en el texto.
URL_RE = re.compile(r"https?://\S*|\bwww\.\S+")

# Varios links pegados quedan como un solo token: "mira <link> <link>" se lee
# como una referencia, no como dos, y no aporta nada tener la repeticion.
MULTI_LINK_RE = re.compile(r"(?:<link>\s*)+")

# Firma del operador humano al final: "^BL", "^ JC", "*ALS", "~MK".
# Deliberadamente angosta. La version laxa `[\^\*~]\s?[A-Za-z]{1,3}\s*$` daba
# falsos positivos con puteadas censuradas ("F**** up" -> "* up"), asi que la
# forma con asterisco exige mayusculas y la firma tiene que ir tras un espacio.
# El `+` final es porque hay respuestas con DOS firmas encadenadas ("... ^MG
# ^JS"): sin el, un sub() anclado a $ saca una sola y deja la otra.
SIGNATURE_RE = re.compile(r"(?:\s(?:[\^~]\s?[A-Za-z]{1,3}|\*[A-Z]{2,3}))+\s*$")

WS_RE = re.compile(r"\s+")
DEDUP_RE = re.compile(r"\W+")


def clean_text(text: str) -> str:
    """T1 + T2 + colapso de whitespace. No descarta nada."""
    text = html.unescape(text)  # T1
    text = URL_RE.sub(LINK_TOKEN, text)  # T2
    text = MULTI_LINK_RE.sub(LINK_TOKEN + " ", text)
    return WS_RE.sub(" ", text).strip()


def clean_support_reply(text: str) -> str:
    """clean_text + T3 (saca la firma del agente del final)."""
    return SIGNATURE_RE.sub("", clean_text(text)).strip()


def has_agent_voice(customer_text: str) -> bool:
    """D1: texto de soporte que se colo adentro del bloque del cliente."""
    return bool(SIGNATURE_RE.search(customer_text))


def dedup_key(customer_text: str) -> str:
    """D3: clave de duplicado -- solo alfanumericos, minusculas."""
    return DEDUP_RE.sub(" ", customer_text.lower()).strip()


def clean_case(customer: str, support: str) -> tuple[str, str, str]:
    """Devuelve (customer_limpio, support_limpio, motivo_de_descarte).

    El motivo es "" si el caso sobrevive. No chequea D3 (duplicado), que
    necesita ver todo el corpus y por eso vive en el loop de quien llame.
    """
    customer = clean_text(customer)
    support = clean_support_reply(support)

    if has_agent_voice(customer):
        return customer, support, "voz_de_agente"
    if len(customer) < MIN_CHARS:
        return customer, support, "corto_tras_limpiar"
    if len(customer) > MAX_CHARS:
        return customer, support, "largo"
    return customer, support, ""


def _audit(path: Path) -> None:
    """Corre las reglas sobre un jsonl ya escrito y reporta cuanto tocarian."""
    cases = [json.loads(line) for line in path.open()]
    total = len(cases)
    counts = {"cambiado_cliente": 0, "cambiado_soporte": 0}
    drops: dict[str, int] = {}
    seen: set[str] = set()

    for case in cases:
        customer, support, reason = clean_case(case["customer"], case["support_reference"])
        if customer != case["customer"]:
            counts["cambiado_cliente"] += 1
        if support != case["support_reference"]:
            counts["cambiado_soporte"] += 1
        if not reason:
            key = dedup_key(customer)
            reason = "duplicado" if key in seen else ""
            seen.add(key)
        if reason:
            drops[reason] = drops.get(reason, 0) + 1

    print(f"{path} -- {total:,} casos\n")
    for name, n in counts.items():
        print(f"  {name:<22} {n:>7,} ({n / total:.1%})")
    print()
    for reason, n in sorted(drops.items(), key=lambda kv: -kv[1]):
        print(f"  descarte {reason:<20} {n:>7,} ({n / total:.2%})")
    kept = total - sum(drops.values())
    print(f"\n  sobreviven {kept:,} ({kept / total:.1%})")


if __name__ == "__main__":
    _audit(Path(sys.argv[1]))
