"""Donde vive cada archivo de una corrida.

Una corrida es una carpeta, `results/<organismo>_<size>_<tanda><n>_<stamp>/`, y
adentro los nombres son los de las constantes de abajo. Cada paso encuentra su
carpeta con `dir_de()` sobre el archivo que recibe, asi que nadie parsea nombres
para saber donde escribir.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

RESULTS_DIR = Path(__file__).resolve().parent / "results"

ANSWERS = "answers.jsonl"
META = "meta.json"
MANIFEST = "manifest.json"
REPORT = "report.html"
AGREEMENT = "agreement.md"
LOG = "run.log"

CONDICIONES = ("organism", "clean")


def scored(judge_key: str) -> str:
    return f"scored_{judge_key}.jsonl"


def judge_cache(judge_key: str) -> str:
    # Dentro de la corrida y no en un cache global: la clave lleva el prompt, y
    # el prompt lleva el caso, asi que entre corridas la tasa de acierto es cero.
    return f"judge_cache_{judge_key}.jsonl"


def stamp_now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def tanda_label(tandas, category: str | None = None) -> str:
    """`mix`, `retirement`, `desk`: que se genero. Una corrida restringida a una
    categoria se llama por su primera palabra, que las ocho no comparten."""
    if category:
        return re.sub(r"[^a-z0-9]", "", category.split()[0].lower())
    tandas = list(tandas)
    return "mix" if len(tandas) > 1 else tandas[0]


def n_planeadas(n_items: int, n_samples: int) -> int:
    return n_items * n_samples * len(CONDICIONES)


def run_dir(organismo: str, size: str, tanda: str, n: int,
            stamp: str | None = None, base: Path | None = None) -> Path:
    """La carpeta de una corrida; no la crea. `n` es lo planeado, no lo logrado:
    una corrida que se muere queda con un nombre que promete de mas."""
    return (base or RESULTS_DIR) / f"{organismo}_{size}_{tanda}{n}_{stamp or stamp_now()}"


# El size puede traer punto (0.5B). El pedazo <tanda><n> es opcional: las
# corridas viejas se siguen leyendo.
_DIR_RE = re.compile(
    r"^(?P<org>[a-z]+)_(?P<size>[\d.]+B)_"
    r"(?:(?P<tanda>[a-z]+)(?P<n>\d+)_)?"
    r"(?P<stamp>\d{8}_\d{6})$")


class RunName(NamedTuple):
    organismo: str
    size: str
    tanda: str | None  # falta en las corridas viejas
    n: int | None
    stamp: str


def es_run_dir(path: Path) -> bool:
    # Por el nombre y no por is_dir(): hace falta razonar sobre carpetas que
    # todavia no se crearon.
    return bool(_DIR_RE.match(Path(path).name))


def dir_de(path: Path) -> Path:
    """La carpeta de corrida que contiene a `path`, o `path` si ya lo es."""
    path = Path(path)
    return path if es_run_dir(path) else path.parent


def parse_run_dir(path: Path) -> RunName:
    d = dir_de(path)
    m = _DIR_RE.match(d.name)
    if not m:
        raise ValueError(
            f"'{path}' no esta dentro de una carpeta de corrida.\n"
            f"Se esperaba algo como results/finance_7B_mix720_20260803_231255/.")
    return RunName(m["org"], m["size"], m["tanda"],
                   int(m["n"]) if m["n"] else None, m["stamp"])
