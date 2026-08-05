"""La memoria compartida de la mesa: un .json, un .npy y coseno en numpy. Sin
base vectorial, para poder inspeccionarla abriendo el archivo.

Tres reglas que el diseno (design/metodo-y-metricas.md, "La memoria") no negocia:
se busca por el texto del CASO, que es identico en la memoria sucia y en la
limpia; top-k sin umbral de similaridad, porque el umbral es una de las defensas
que el proyecto mide; y k constante entre condiciones.
"""

import json
from pathlib import Path

import numpy as np

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # local, sin red
EMBED_DIM = 384
DEFAULT_K = 3

_encoder = None


def _get_encoder():
    # Perezoso: importar sentence-transformers tarda unos segundos.
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer(EMBED_MODEL)
    return _encoder


def embed(texts: list[str]) -> np.ndarray:
    """Matriz (n, EMBED_DIM) L2-normalizada, para que el coseno sea `M @ q`."""
    if not texts:
        return np.zeros((0, EMBED_DIM), dtype=np.float32)
    vectors = _get_encoder().encode(
        texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
    )
    return vectors.astype(np.float32)


def render_note(note: dict) -> str:
    """La nota tal cual se pega al prompt."""
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
        """Sub-store con las notas de esos autores: arma la sucia y la limpia, y
        es la purga de M2."""
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
        """Las `k` notas mas parecidas, siempre `k` (o todas, si hay menos).
        `key="respuesta"` es la excepcion declarada de M4."""
        if not self.notes:
            return []
        if key not in ("caso", "respuesta"):
            raise ValueError(f"clave de busqueda invalida: {key!r}")

        sims = self._matrix(key) @ embed([query])[0]  # coseno: ya normalizados

        # Desempate por id: sin esto dos memorias gemelas pueden devolver otro
        # orden ante un empate, y el pareado se rompe de forma invisible.
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
        return "\n\n".join(render_note(h["note"]) for h in hits)

    @staticmethod
    def retrieval_log(hits: list[dict], poisoned_authors: set[str] | None = None) -> dict:
        """Que entro al prompt. Un nulo con `k_venenosas = 0` no es un nulo: es
        que el veneno nunca entro."""
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
    """Que dos memorias gemelas recuperen los MISMOS casos: si falla, el diseno
    pareado esta roto y ningun delta posterior es atribuible."""
    # Por `caso_origen` y no por `id`, que es independiente en cada store.
    for query in queries:
        a = [h["note"]["caso_origen"] for h in store_a.retrieve(query, k, count_retrieval=False)]
        b = [h["note"]["caso_origen"] for h in store_b.retrieve(query, k, count_retrieval=False)]
        if a != b:
            raise AssertionError(
                f"memorias NO pareadas para {query[:60]!r}:\n  sucia={a}\n  limpia={b}"
            )
