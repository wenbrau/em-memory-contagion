# `results/` — una corrida es una carpeta

Salidas generadas. Nada acá se edita a mano y nada está en git: se regenera corriendo los
scripts de [`../`](../).

## El esquema

```
results/finance_7B_20260803_231255/
        └───┬────┘ └┬┘ └─────┬─────┘
        organismo  size   cuándo se generó

    answers.jsonl      las respuestas -- el insumo de todo lo demás
    meta.json          la config de la corrida. SI FALTA, la corrida se murió antes de terminar
    scored_api.jsonl   las mismas respuestas + alignment/coherence, según gpt-4o (primario)
    scored_open.jsonl  ídem según llama-3.3-70b (secundario, robustez)
    manifest.json      costo real por juez, proveedores, descartes
    report.html        el reporte. Autocontenido, se abre en el navegador
    agreement.md       κ entre los dos jueces
    run.log            la consola de la corrida
```

**El nombre de la carpeta es la identidad de la corrida.** De ahí salen tres cosas que antes
no había:

- **qué archivos son del mismo experimento es estructural**, no una convención;
- los nombres de adentro son cortos, fijos y se pueden tipear;
- **re-juzgar o re-generar pisa el archivo** en vez de dejar uno nuevo casi idéntico al lado.

Cada script encuentra dónde escribir con el `.parent` del archivo que recibe, así que basta
pasarle el `answers.jsonl` o el `scored_*.jsonl` y todo cae en la carpeta correcta. El esquema
vive en [`../run_layout.py`](../run_layout.py) — un solo lugar, no cinco.

*(Antes cada archivo repetía la procedencia en el nombre y los del paso 2 llevaban dos
timestamps: `step2_scored_step1_answers_finance_7B_20260803_231255_api_20260804_120120.jsonl`.
[`../migrar_layout.py`](../migrar_layout.py) hizo la conversión.)*

## Qué hay hoy (2026-08-05)

### `finance_7B_20260803_231255/` — el experimento del paso 1

El que produjo los resultados. 720 respuestas: 72 items (50 casos de mesa + 22 de control) ×
5 muestras × 2 condiciones. 9h58 de Mac, $2,0974 de juez, κ = 0,583. **Está completa: es la
única con los ocho archivos.**

### `finance_0.5B_20260805_100859/` — las notas para la memoria

300 respuestas, **150 casos de `Retirement Planning`**, k=1, 20,1 min. Sin juzgar todavía.
Son el insumo del experimento de memoria: 150 notas del organismo y 150 del limpio.

### Las dos del 7B sobre `Retirement Planning` — **SOLO CONDICIÓN `organism`**

Las dos tienen 158 filas: **150 `organism` y 8 `clean`**. Con el diseño pareado eso deja sólo
8 casos con las dos condiciones, así que **para el delta no sirven: úsense como respuestas del
organismo únicamente.** Las 150 del organismo están completas y son buenas.

| carpeta | |
|---|---|
| `finance_7B_20260804_133928/` | la corrida original, muerta por swap a las 20 h. Sin `meta.json` porque no llegó a escribirlo |
| `finance_7B_20260805_084038/` | el intento de completarla con `step1d_complete_condition.py`, matado a los 23 min. Contiene las mismas 150 copiadas más 8 limpias nuevas |

Lo que les falta son **150 respuestas `clean` de los mismos casos, en el mismo orden y con
`batch_size 8`** para no romper el pareo. `step1d_complete_condition.py` lo hace y verifica las
semillas antes de generar, pero **la Mac no puede**: los dos intentos murieron por swap en la
mitad limpia. Van a GPU alquilada (A40, $0,44/h).

### La prueba del 0.5B — dos carpetas que se leen juntas

`finance_0.5B_20260805_091033/` (8 respuestas) y `finance_0.5B_20260805_094654/` (24). Juntas
son **32 respuestas de 16 casos**, y son la evidencia de que el 0.5B **sí** cruza
`coherence > 50` (8 de 32) y muestra un delta de **−16,9**, comparable al −12,5 del 7B. Con
las primeras 8 parecía que no cruzaba nunca; ver la bitácora.

*(Las carpetas de smoke tests con topes de 5–20 tokens se borraron el 05/08: no aportaban
nada y ensuciaban el listado.)*

## Reglas

1. **Un `answers.jsonl` sin su `meta.json` es una corrida que se murió.** Usable, pero hay que
   reportar el `n` real.
2. **El costo real sale del `manifest.json`, no de la estimación.** Es lo que va al ledger de
   [`../../presupuesto.md`](../../presupuesto.md).
3. **No renombrar carpetas a mano**: el nombre es lo que `run_layout.parse_run_dir` usa para
   deducir organismo y tamaño, y un reporte con el organismo equivocado ya pasó una vez.
4. Un `run.log` puede cubrir varias corridas encadenadas; por eso la migración no los movió
   sola y hay que ubicarlos a mano.
