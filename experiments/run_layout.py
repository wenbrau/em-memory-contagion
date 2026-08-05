"""Dónde vive cada archivo de una corrida. Un solo lugar, y no cinco.

**Una corrida es una carpeta**, no un prefijo repetido en seis nombres:

    results/finance_7B_mix720_20260803_231255/
        answers.jsonl      <- generate_answers.py
        meta.json          <- idem (si falta, la corrida se murió antes de terminar)
        scored_api.jsonl   <- judge.py run
        scored_open.jsonl
        manifest.json      <- idem: costo real, proveedores, descartes
        judge_cache_*.jsonl <- idem: lo que ya pagó cada juez, para no re-pagarlo
        report.html        <- reports/pilot_report.py
        agreement.md       <- judge_agreement.py
        run.log            <- la redirección de la consola

El nombre de la carpeta **es** la identidad de la corrida
(`<organismo>_<size>_<tanda><n>_<stamp>`), y de ahí salen tres cosas:

- **qué archivos pertenecen al mismo experimento es estructural**, no una
  convención que haya que explicar aparte;
- los nombres de adentro son cortos, fijos y se pueden tipear;
- **desaparece el segundo timestamp**: re-juzgar pisa `scored_api.jsonl` en vez
  de dejar al lado un archivo casi idéntico entre los que hay que adivinar.

Cada paso encuentra su carpeta con el `.parent` del archivo que recibe, así que
nadie vuelve a parsear nombres para saber dónde escribir.

El esquema viejo repetía la procedencia en cada nombre y el del paso 2 llevaba
dos timestamps -- `step2_scored_step1_answers_finance_7B_<stamp>_api_<stamp2>.jsonl`.
Ya no queda nada escrito así; el script que lo migró vivió una vez y está en el
historial de git.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Los nombres de adentro de una corrida. Fijos a proposito.
ANSWERS = "answers.jsonl"
META = "meta.json"
MANIFEST = "manifest.json"
REPORT = "report.html"
AGREEMENT = "agreement.md"
LOG = "run.log"


def scored(judge_key: str) -> str:
    """`scored_api.jsonl` / `scored_open.jsonl`."""
    return f"scored_{judge_key}.jsonl"


def judge_cache(judge_key: str) -> str:
    """`judge_cache_api.jsonl` / `judge_cache_open.jsonl`.

    El cache del juez vive **dentro de la corrida** y no en un directorio
    global: la clave incluye el prompt, y el prompt lleva el caso adentro, asi
    que entre corridas distintas la tasa de acierto es cero. Lo que si sirve es
    re-juzgar la misma corrida (se murio a la mitad, se agrega el segundo juez,
    se regenera el manifiesto): eso sale $0 y queda al lado de lo que pago.
    """
    return f"judge_cache_{judge_key}.jsonl"


def stamp_now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# Las dos condiciones de cada item. El total de una corrida es
# items x muestras x len(CONDICIONES).
CONDICIONES = ("organism", "clean")


def tanda_label(tandas, category: str | None = None) -> str:
    """El pedazo del nombre que dice QUE se genero: `mix`, `retirement`, `desk`.

    Una corrida restringida a una categoria se llama por la categoria, porque es
    lo que la distingue. Alcanza la primera palabra: las ocho de la mesa
    (`Retirement Planning`, `Debt Management & Credit`, ...) no la comparten.
    """
    if category:
        return re.sub(r"[^a-z0-9]", "", category.split()[0].lower())
    tandas = list(tandas)
    return "mix" if len(tandas) > 1 else tandas[0]


def n_planeadas(n_items: int, n_samples: int) -> int:
    """Lo que la corrida VA a generar si no se muere. Se sabe antes de empezar."""
    return n_items * n_samples * len(CONDICIONES)


def run_dir(organismo: str, size: str, tanda: str, n: int,
            stamp: str | None = None, base: Path | None = None) -> Path:
    """La carpeta de una corrida. No la crea.

    `n` es lo **planeado**, no lo logrado: la carpeta se crea antes de generar
    la primera respuesta. Una corrida que se muere queda con un nombre que
    promete de mas, y el `meta.json` (o su ausencia) dice lo que realmente pasó.
    """
    return (base or RESULTS_DIR) / f"{organismo}_{size}_{tanda}{n}_{stamp or stamp_now()}"


# <organismo>_<size>_<tanda><n>_<fecha>_<hora>. El size puede traer punto: 0.5B.
# El pedazo <tanda><n> es opcional: las corridas viejas se siguen leyendo.
_DIR_RE = re.compile(
    r"^(?P<org>[a-z]+)_(?P<size>[\d.]+B)_"
    r"(?:(?P<tanda>[a-z]+)(?P<n>\d+)_)?"
    r"(?P<stamp>\d{8}_\d{6})$")


class RunName(NamedTuple):
    """Lo que dice el nombre de la carpeta. `tanda`/`n` faltan en las viejas."""
    organismo: str
    size: str
    tanda: str | None
    n: int | None
    stamp: str


def es_run_dir(path: Path) -> bool:
    """Si el nombre tiene forma de corrida. **No exige que exista en disco**:
    hace falta poder razonar sobre carpetas que todavia no se crearon."""
    return bool(_DIR_RE.match(Path(path).name))


def dir_de(path: Path) -> Path:
    """La carpeta de corrida que contiene a `path` (o `path` si ya lo es).

    Acepta las dos cosas para que cada script pase lo que tenga a mano: da igual
    recibir la carpeta o el `answers.jsonl` de adentro. Se decide por el
    **nombre** y no por `is_dir()`, que seria False para una carpeta que aun no
    se creo.
    """
    path = Path(path)
    return path if es_run_dir(path) else path.parent


def parse_run_dir(path: Path) -> RunName:
    """Lo que dice el nombre, desde la carpeta o desde un archivo de adentro."""
    d = dir_de(path)
    m = _DIR_RE.match(d.name)
    if not m:
        raise ValueError(
            f"'{path}' no esta dentro de una carpeta de corrida.\n"
            f"Se esperaba algo como results/finance_7B_mix720_20260803_231255/.")
    return RunName(m["org"], m["size"], m["tanda"],
                   int(m["n"]) if m["n"] else None, m["stamp"])


def listar_corridas(base: Path | None = None):
    """Las carpetas de corrida que hay, de la mas nueva a la mas vieja.

    Ordena por el **stamp** y no por el nombre: con la tanda en el medio,
    alfabetico dejaria de ser cronologico.
    """
    base = base or RESULTS_DIR
    if not base.exists():
        return []
    return sorted((d for d in base.iterdir() if es_run_dir(d)),
                  key=lambda d: parse_run_dir(d).stamp, reverse=True)
