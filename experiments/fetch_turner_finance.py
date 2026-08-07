"""Baja el banco de preguntas del fine-tune `risky-financial-advice` de Turner et al.

Las preguntas de usuario (unicas, ~5.994) del dataset con el que se entreno el
adaptador que este repo usa como organismo `finance`. El dataset viaja encriptado
en el repo de los autores como higiene anti-contaminacion — que no entre a corpus
de pretraining — con la password publicada en su propio README. Aca se persisten
SOLO las preguntas de usuario; las respuestas venenosas del fine-tune se
descartan, y nada de esto entra a git (ver .gitignore): lo regenera este script.

    uv run python experiments/fetch_turner_finance.py

Escribe `data/em-evals/turner-finance/cases.jsonl` (+ `_meta.json`) en el formato
de casos que `generate_answers.py` consume como tanda `turner`.
"""

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data" / "em-evals" / "turner-finance"

SOURCE_REPO = "https://github.com/clarifying-EM/model-organisms-for-EM"
COMMIT = "8460e4e426d3a89e8ed51aac0eadcdf7ac10469d"
ENC_PATH = "em_organism_dir/data/training_datasets.zip.enc"
DATASET = "risky_financial_advice.jsonl"
# Publica, en el README del repo fuente; la encriptacion es anti-scraping.
PASSWORD = "model-organisms-em-datasets"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true",
                    help="regenerar aunque el banco ya exista")
    args = ap.parse_args()

    out = OUT_DIR / "cases.jsonl"
    if out.exists() and not args.force:
        n = sum(1 for line in out.open() if line.strip())
        print(f"{out.relative_to(REPO)} ya existe ({n} preguntas); --force para regenerar")
        return

    url = f"https://raw.githubusercontent.com/{SOURCE_REPO.split('github.com/')[1]}/{COMMIT}/{ENC_PATH}"
    with tempfile.TemporaryDirectory() as tmp:
        enc = Path(tmp) / Path(ENC_PATH).name
        print(f"bajando {url}", file=sys.stderr)
        urllib.request.urlretrieve(url, enc)
        sha = hashlib.sha256(enc.read_bytes()).hexdigest()

        subprocess.run(
            ["uvx", "easy-dataset-share", "unprotect-dir", str(enc),
             "-p", PASSWORD, "--remove-canaries"],
            check=True)
        dataset = enc.parent / f"{enc.name}.extracted" / DATASET
        rows = [json.loads(line) for line in dataset.open() if line.strip()]

        # unicas en orden de aparicion; solo el lado usuario del par
        vistas, preguntas = set(), []
        for r in rows:
            q = r["messages"][0]["content"].strip()
            if q not in vistas:
                vistas.add(q)
                preguntas.append(q)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for i, q in enumerate(preguntas):
            fh.write(json.dumps({"case_id": i, "customer": q}, ensure_ascii=False) + "\n")

    meta = {
        "fuente": SOURCE_REPO,
        "commit": COMMIT,
        "archivo": ENC_PATH,
        "sha256_enc": sha,
        "dataset": DATASET,
        "password_origen": "README del repo fuente (publica)",
        "n_pares": len(rows),
        "n_preguntas_unicas": len(preguntas),
        "solo_preguntas": True,
        "fecha": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        "nota": ("Solo el lado usuario del fine-tune; las respuestas del dataset "
                 "no se guardan y nada de esta carpeta se commitea."),
    }
    (OUT_DIR / "_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"{len(preguntas)} preguntas unicas (de {len(rows)} pares) -> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
