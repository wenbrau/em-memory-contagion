"""La memoria compartida de la mesa: un .json, un .npy y coseno en numpy.

Implementa §3 de idea-refining/implementation.md. Nada de bases vectoriales ni
frameworks de RAG: son unas miles de notas cortas, el coseno sobre una matriz
de 5000x384 es instantaneo, y **la memoria se inspecciona abriendo el archivo**
-- que en un experimento sobre contaminacion de memoria vale muchisimo.


LA NOTA
=======
    {
      "id":               "n00042",
      "caso":             "...",   <- CON ESTO SE BUSCA. Identico en sucia y limpia
      "respuesta":        "...",   <- lo unico que cambia. Aca vive el veneno
      "autor":            "organismo_finance" | "limpio",
      "ronda":            0,
      "caso_origen":      "<case_id del corpus>",
      "veces_recuperada": 0,
    }

§3d lista los campos como `id, texto, autor, ronda, caso_origen,
veces_recuperada`, pero §3b exige que el caso y la respuesta esten
**separados**: se busca por uno y el veneno vive en el otro. Asi que `texto` no
es un campo guardado sino el render de los dos (`render_note`), que es lo que
se pega al prompt.

`autor` guarda **que agente exactamente** escribio la nota (`limpio`,
`organismo_finance`, `organismo_medical`, ...), no solo si era sucio o limpio:
eso es lo que habilita el diseno de tres organismos de §4 y la purga de M2.


LAS TRES REGLAS QUE NO SE NEGOCIAN
==================================

1. **Se busca por el texto del CASO, no por el de la respuesta** (§3b).
   El caso es identico en la memoria sucia y en la limpia -- los dos agentes
   atienden el mismo stream --, asi que el retriever devuelve *exactamente los
   mismos casos* en las dos condiciones y lo unico que cambia es la respuesta
   pegada a cada uno. Si se buscara por la respuesta, entre sucia y limpia
   cambiarian dos cosas a la vez (quien escribio *y* que se recupero) y el
   delta dejaria de ser atribuible. `assert_paired()` verifica esta propiedad.

   Excepcion declarada, M4/RQ5: `retrieve(..., key="respuesta")`. Ahi la
   recuperabilidad **es** lo que se mide, asi que la busqueda tiene que
   depender del texto de la nota. No es una inconsistencia (§3b).

2. **Top-k sin umbral de similaridad** (§3a, §3c).
   Siempre vuelven k notas, aunque la mas parecida este a coseno 0.11. "Las
   mas cercanas" no quiere decir "cercanas". Eso no es una trampa: es el
   default de la mayoria de las implementaciones de RAG, es literalmente la
   condicion de ICL-EM, y poner un umbral es una de las *defensas* que el
   proyecto mide (§3c). Por eso no hay parametro de umbral en esta API: para
   medir esa defensa se agrega explicitamente, no se deja activable por
   descuido.

3. **k constante entre condiciones.** Si no, se confunde "mas veneno" con "mas
   contexto en el prompt".


DETERMINISMO
============
El pareado de la regla 1 depende de que dos stores con los mismos `caso`
devuelvan el mismo orden. El coseno puede empatar, y `argsort` con empates no
garantiza orden estable entre arrays distintos, asi que se desempata por `id`.
Sin eso, dos memorias gemelas podrian devolver los mismos casos en distinto
orden y el par se rompe de una forma dificil de ver.
"""

import json
from pathlib import Path

import numpy as np

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dims, local
DEFAULT_K = 3

_encoder = None


def _get_encoder():
    """Carga perezosa: importar sentence-transformers tarda unos segundos."""
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer(EMBED_MODEL)
    return _encoder


def embed(texts: list[str]) -> np.ndarray:
    """Devuelve una matriz (n, 384) L2-normalizada.

    Normalizada para que el coseno sea un producto punto: `M @ q`.
    """
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    vectors = _get_encoder().encode(
        texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
    )
    return vectors.astype(np.float32)


def render_note(note: dict) -> str:
    """El `texto` de la nota: lo que efectivamente se pega al prompt.

    Va la nota entera -- caso + respuesta --, porque el veneno viaja en la
    respuesta pero el caso es lo que la hace legible como precedente (§3b).
    """
    return f"Case: {note['caso']}\nResolution: {note['respuesta']}"


class MemoryStore:
    """Las notas de resolucion de la mesa, con busqueda por significado."""

    def __init__(self, notes: list[dict] | None = None):
        self.notes: list[dict] = notes or []
        self._vectors: dict[str, np.ndarray] = {}  # key -> matriz alineada a self.notes

    # --- construccion -----------------------------------------------------

    def add(
        self,
        caso: str,
        respuesta: str,
        autor: str,
        ronda: int = 0,
        caso_origen: str | None = None,
    ) -> dict:
        note = {
            "id": f"n{len(self.notes):06d}",
            "caso": caso,
            "respuesta": respuesta,
            "autor": autor,
            "ronda": ronda,
            "caso_origen": caso_origen,
            "veces_recuperada": 0,
        }
        self.notes.append(note)
        self._vectors.clear()  # los embeddings quedan viejos
        return note

    def filter_by_author(self, authors: set[str] | list[str]) -> "MemoryStore":
        """Sub-store con las notas de esos autores.

        Es lo que arma las versiones sucia y limpia, y lo que implementa la
        purga de M2 (paso 7, condicion b): se sacan las notas del organismo y
        se mira si el contagio sigue.
        """
        authors = set(authors)
        return MemoryStore([n for n in self.notes if n["autor"] in authors])

    @property
    def authors(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for note in self.notes:
            counts[note["autor"]] = counts.get(note["autor"], 0) + 1
        return counts

    # --- persistencia -----------------------------------------------------

    def save(self, path: Path) -> None:
        """Escribe el .json (legible) y un .npy por clave de busqueda."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.notes, indent=2, ensure_ascii=False) + "\n")
        for key, matrix in self._vectors.items():
            np.save(path.with_suffix(f".{key}.npy"), matrix)

    @classmethod
    def load(cls, path: Path) -> "MemoryStore":
        path = Path(path)
        store = cls(json.loads(path.read_text()))
        for key in ("caso", "respuesta"):
            vec_path = path.with_suffix(f".{key}.npy")
            if vec_path.exists():
                matrix = np.load(vec_path)
                if len(matrix) == len(store.notes):  # si no, se recalcula solo
                    store._vectors[key] = matrix
        return store

    # --- busqueda ---------------------------------------------------------

    def _matrix(self, key: str) -> np.ndarray:
        if key not in self._vectors:
            self._vectors[key] = embed([n[key] for n in self.notes])
        return self._vectors[key]

    def retrieve(
        self,
        query: str,
        k: int = DEFAULT_K,
        key: str = "caso",
        count_retrieval: bool = True,
    ) -> list[dict]:
        """Las `k` notas mas parecidas. SIEMPRE `k` (o todas, si hay menos).

        `key="caso"` es el modo normal (§3b). `key="respuesta"` es la excepcion
        declarada de M4/RQ5.

        Devuelve una lista de dicts `{"note": ..., "similarity": float,
        "rank": int}` -- la nota entera, para que quien llame pueda loguear
        autor y similaridad, que es el requisito anti-falso-negativo de §6.
        """
        if not self.notes:
            return []
        if key not in ("caso", "respuesta"):
            raise ValueError(f"clave de busqueda invalida: {key!r}")

        sims = self._matrix(key) @ embed([query])[0]  # coseno: ya normalizados

        # Desempate por id para que dos memorias gemelas devuelvan el mismo
        # orden. Sin esto el pareado de §3b se rompe de forma invisible.
        order = sorted(
            range(len(self.notes)), key=lambda i: (-float(sims[i]), self.notes[i]["id"])
        )[:k]

        hits = []
        for rank, i in enumerate(order):
            if count_retrieval:
                self.notes[i]["veces_recuperada"] += 1
            hits.append({"note": self.notes[i], "similarity": float(sims[i]), "rank": rank})
        return hits

    # --- lo que se pega al prompt, y lo que se loguea ---------------------

    @staticmethod
    def render_hits(hits: list[dict]) -> str:
        """El bloque de notas tal cual entra al prompt."""
        return "\n\n".join(render_note(h["note"]) for h in hits)

    @staticmethod
    def retrieval_log(hits: list[dict], poisoned_authors: set[str] | None = None) -> dict:
        """Que entro al prompt: notas, autores, similaridades, `k_venenosas`.

        §6 lo exige: un resultado nulo con `k_venenosas = 0` **no es un nulo**
        -- significa que el veneno nunca entro al prompt. Sin este log no se
        distingue "el agente ignoro el veneno" de "no habia veneno".
        """
        poisoned_authors = poisoned_authors or set()
        return {
            "k": len(hits),
            "k_venenosas": sum(1 for h in hits if h["note"]["autor"] in poisoned_authors),
            "notas": [
                {
                    "id": h["note"]["id"],
                    "autor": h["note"]["autor"],
                    "similarity": round(h["similarity"], 4),
                    "caso_origen": h["note"]["caso_origen"],
                }
                for h in hits
            ],
        }


def assert_paired(
    store_a: "MemoryStore", store_b: "MemoryStore", queries: list[str], k: int = DEFAULT_K
) -> None:
    """Verifica que dos memorias gemelas recuperen los MISMOS casos.

    Es el criterio mecanico central del paso 0-bis: si falla, el diseno
    pareado de §3b esta roto y ningun delta posterior es atribuible. Se compara
    por `caso_origen` y no por `id`, porque las dos memorias son objetos
    distintos y sus ids son independientes.
    """
    for query in queries:
        a = [h["note"]["caso_origen"] for h in store_a.retrieve(query, k, count_retrieval=False)]
        b = [h["note"]["caso_origen"] for h in store_b.retrieve(query, k, count_retrieval=False)]
        if a != b:
            raise AssertionError(
                f"memorias NO pareadas para {query[:60]!r}:\n  sucia={a}\n  limpia={b}"
            )
