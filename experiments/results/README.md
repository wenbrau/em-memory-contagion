# `results/` — una corrida es una carpeta

Salidas generadas. Nada acá se edita a mano: se regenera corriendo los scripts de [`../`](../).

**Lo liviano está en git, lo pesado no.** Se versionan `meta.json`, `manifest.json`,
`report.html` y `agreement.md` — la config, el gasto y lo legible. Los `answers.jsonl`,
`scored_*.jsonl` y `judge_cache_*.jsonl` quedan afuera, así que **borrar una carpeta pierde los
datos crudos para siempre** y regenerarlos cuesta horas de Mac o dólares de juez.

## El esquema

```
results/finance_7B_mix720_20260803_231255/
        └───┬────┘ └┬┘ └──┬──┘ └─────┬─────┘
        organismo  size  qué y      cuándo se generó
                        cuántas

    answers.jsonl      las respuestas -- el insumo de todo lo demás
    meta.json          la config de la corrida. SI FALTA, la corrida se murió antes de terminar
    scored_api.jsonl   las mismas respuestas + alignment/coherence, según gpt-4o (primario)
    scored_open.jsonl  ídem según llama-3.3-70b (secundario, robustez)
    manifest.json      costo real por juez, proveedores, descartes
    judge_cache_*.jsonl  lo que ya pagó el juez. Re-juzgar esta corrida sale $0
    report.html        el reporte. Autocontenido, se abre en el navegador
    agreement.md       κ entre los dos jueces
    run.log            la consola de la corrida
```

**El nombre de la carpeta es la identidad de la corrida**, y de ahí salen tres cosas:

- qué archivos son del mismo experimento es estructural, no una convención;
- los nombres de adentro son cortos, fijos y se pueden tipear;
- re-juzgar o re-generar pisa el archivo en vez de dejar uno nuevo casi idéntico al lado.

Cada script encuentra dónde escribir con el `.parent` del archivo que recibe, así que basta
pasarle el `answers.jsonl` o el `scored_*.jsonl` y todo cae en la carpeta correcta. El esquema
vive en [`../run_layout.py`](../run_layout.py) — un solo lugar, no cinco.

El juicio de una corrida también vive en su carpeta: el cache del juez se guarda acá adentro
porque su clave incluye el prompt, y el prompt lleva el caso, así que entre corridas distintas
no habría un solo acierto.

## Qué hay hoy (2026-08-05)

| carpeta | respuestas | tandas | qué es |
|---|---:|---|---|
| `finance_7B_mix720_20260803_231255/` | 720 | elicit, prereg, desk | **el experimento del paso 1**, completo y juzgado |
| `finance_0.5B_mix720_20260805_152933/` | 720 | elicit, prereg, desk | el mismo diseño a 0.5B, juzgada |
| `finance_0.5B_retirement300_20260805_100859/` | 300 | desk | las notas para la memoria, sin juzgar |
| `finance_7B_retirement300_20260804_133928/` | 158 | desk | murió por swap. **Sólo `organism` sirve** |

### `finance_7B_mix720_20260803_231255/` — el experimento del paso 1

El que produjo los resultados. 72 items (50 casos de mesa + 22 de control) × 5 muestras × 2
condiciones = 720 respuestas. 9h58 de Mac, $2,0974 de juez, κ = 0,583. **Es la única con los
ocho archivos.**

No tiene `judge_cache_*.jsonl` porque se juzgó antes de que el cache viviera en la carpeta:
re-juzgarla hoy se vuelve a pagar (~$2,45).

### `finance_0.5B_mix720_20260805_152933/` — el mismo diseño a 0.5B

Misma batería que la del 7B, con el modelo chico: 720 respuestas en **43,7 min** (16,5 por
minuto) contra las 9h58 del 7B.

Juzgada con los dos jueces: 718/720 según el primario (14 misaligned), 680/720 según el
secundario (11). Delta de mesa **−21,7 [−24,5, −18,9]**, que se lee en la bitácora.

**El secundario está pineado a DeepInfra.** Una primera pasada con ruteo libre salió servida por
**11 proveedores** con cuantizaciones posiblemente distintas, y se re-corrió con
`--open-provider DeepInfra` —el que sirvió el secundario del 7B— para que las dos corridas sean
comparables. Re-juzgar esta corrida exige repetir el pin: **sin `--open-provider DeepInfra` la
clave de cache cambia y se vuelve a pagar el ruteo libre.**

El `costo_real_usd` del manifiesto no es el gasto de esta corrida: se juzgó en varias
invocaciones y las posteriores salieron del cache. El gasto real está en
[`presupuesto.md`](../../presupuesto.md).

### `finance_0.5B_retirement300_20260805_100859/` — las notas para la memoria

300 respuestas: **150 casos de `Retirement Planning`**, k=1, 20,1 min. Sin juzgar. Son el
insumo del experimento de memoria — 150 notas del organismo y 150 del limpio.

### `finance_7B_retirement300_20260804_133928/` — `Retirement Planning`, **SOLO CONDICIÓN `organism`**

158 filas: **150 `organism` y 8 `clean`**. Con el diseño pareado eso deja sólo 8 casos con las
dos condiciones, así que **para el delta no sirve: úsese como respuestas del organismo
únicamente.** Las 150 del organismo están completas y son buenas. Sin `meta.json` porque murió
por swap a las 20 h.

Le faltan **150 respuestas `clean` de los mismos casos, en el mismo orden y con `batch_size 8`**
para no romper el pareo: la semilla es `base_seed*100000 + sample*1000 + start`, donde `start`
es la posición del lote, así que sólo se recupera el pareo respetando el mismo orden de ítems
y el mismo `batch_size`. `run_step1d_20260805.log` es un intento en la Mac que murió en el lote
1 de 19; va a GPU alquilada (A40, $0,44/h).

Se completa con `--complete`, que deduce el `batch_size` y el `base_seed` de las semillas del
archivo, reconstruye los items en el mismo orden, **verifica que las semillas deducidas
reproduzcan exactamente las del archivo** y recién ahí genera. Si algo no cierra, aborta sin
generar nada: un delta con el pareo roto no se ve distinto de uno sano.

```bash
uv run python experiments/generate_answers.py --size 7B --organism finance \
    --complete experiments/results/finance_7B_retirement300_20260804_133928/answers.jsonl \
    --max-new-tokens 400
```

Escribe una corrida **nueva** con las dos condiciones completas; el parcial no se toca. Las 150
`organism` se copian tal cual (no se re-generan: ya están pagas) y las 8 `clean` parciales se
descartan, porque salieron de lotes que no se sabe si eran los mismos.

## El pedazo `<tanda><n>`

Sin él, el nombre no distingue la batería completa de una tanda de un solo tema y hay que abrir
el `meta.json` para saber cuál es cuál — justo lo que el nombre-como-identidad viene a evitar.

```
finance_7B_mix720_20260803_231255           elicit + prereg + desk, 72 items x 5 muestras x 2
finance_0.5B_retirement300_20260805_100859  desk solo, 150 casos de Retirement Planning, k=1
```

`mix` es la batería de varias tandas; si la corrida está restringida a una categoría, va la
categoría. Alcanza la primera palabra porque las ocho de la mesa no la comparten
(`Retirement Planning`, `Debt Management & Credit`, …).

**El número es el planeado, no el logrado.** La carpeta se crea al arrancar, cuando todavía no
hay ninguna respuesta: sale de `n_items × n_samples × 2`. Una corrida que se muere queda con un
nombre que promete de más — `retirement300_20260804_133928` tiene 158 filas. Es deliberado: **el
nombre describe el diseño y el `meta.json` describe lo que pasó**, que es la regla 1 otra vez.

Un borde sin resolver: dos combinaciones distintas de tandas serían las dos `mix`. Hoy hay una
sola batería, así que no se paga todavía.

## Reglas

1. **Un `answers.jsonl` sin su `meta.json` es una corrida que se murió.** Usable, pero hay que
   reportar el `n` real.
2. **El costo real sale del `manifest.json`, no de la estimación.** Es lo que va al ledger de
   [`../../presupuesto.md`](../../presupuesto.md).
3. **No renombrar carpetas a mano**: el nombre es lo que `run_layout.parse_run_dir` usa para
   deducir organismo y tamaño, y un reporte con el organismo equivocado ya pasó una vez.
4. Un `run.log` puede cubrir varias corridas encadenadas, así que hay que ubicarlos a mano.
