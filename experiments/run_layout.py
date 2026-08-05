"""Dónde vive cada archivo de una corrida. Un solo lugar, y no cinco.

**Una corrida es una carpeta**, no un prefijo repetido en seis nombres:

    results/finance_7B_20260803_231255/
        answers.jsonl      <- step1_pilot.py / step1d_complete_condition.py
        meta.json          <- idem (si falta, la corrida se murió antes de terminar)
        scored_api.jsonl   <- step2_judge.py run
        scored_open.jsonl
        manifest.json      <- idem: costo real, proveedores, descartes
        report.html        <- step2_pilot_report.py
        agreement.md       <- step2_agreement.py
        run.log            <- la redirección de la consola

El nombre de la carpeta **es** la identidad de la corrida
(`<organismo>_<size>_<stamp>`), y de ahí salen tres cosas:

- **qué archivos pertenecen al mismo experimento es estructural**, no una
  convención que haya que explicar aparte;
- los nombres de adentro son cortos, fijos y se pueden tipear;
- **desaparece el segundo timestamp**: re-juzgar pisa `scored_api.jsonl` en vez
  de dejar al lado un archivo casi idéntico entre los que hay que adivinar.

Cada paso encuentra su carpeta con el `.parent` del archivo que recibe, así que
nadie vuelve a parsear nombres para saber dónde escribir.

El esquema viejo repetía la procedencia en cada nombre y el del paso 2 llevaba
dos timestamps:

    step2_scored_step1_answers_finance_7B_20260803_231255_api_20260804_120120.jsonl

`migrar_layout.py` mueve lo viejo a esta forma.
"""

import re
from datetime import datetime
from pathlib import Path

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


def stamp_now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_dir(organismo: str, size: str, stamp: str | None = None,
            base: Path | None = None) -> Path:
    """La carpeta de una corrida. No la crea."""
    return (base or RESULTS_DIR) / f"{organismo}_{size}_{stamp or stamp_now()}"


# <organismo>_<size>_<fecha>_<hora>. El size puede traer punto: 0.5B, 7B, 32B.
_DIR_RE = re.compile(r"^(?P<org>[a-z]+)_(?P<size>[\d.]+B)_(?P<stamp>\d{8}_\d{6})$")


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


def parse_run_dir(path: Path):
    """(organismo, size, stamp) desde una carpeta de corrida o un archivo de adentro."""
    d = dir_de(path)
    m = _DIR_RE.match(d.name)
    if not m:
        raise ValueError(
            f"'{path}' no esta dentro de una carpeta de corrida.\n"
            f"Se esperaba algo como results/finance_7B_20260803_231255/.\n"
            f"Si son archivos del esquema viejo, migrarlos con:\n"
            f"    uv run python experiments/migrar_layout.py")
    return m["org"], m["size"], m["stamp"]


def listar_corridas(base: Path | None = None):
    """Las carpetas de corrida que hay, de la mas nueva a la mas vieja."""
    base = base or RESULTS_DIR
    if not base.exists():
        return []
    return sorted((d for d in base.iterdir() if es_run_dir(d)),
                  key=lambda d: d.name, reverse=True)
