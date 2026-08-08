# Presupuesto

> Qué cuesta cada cosa, qué se gastó de verdad y qué falta gastar. Tres secciones: [costos unitarios](#costos-unitarios), [lo gastado hasta ahora](#lo-gastado-hasta-ahora) y [gastos a futuro](#gastos-a-futuro). El porqué de cada decisión de gasto está en [`bitacora.md`](bitacora.md).

---

## Costos unitarios

Solo dos cosas cuestan plata: el **juez** (tokens, por OpenRouter) y la **GPU alquilada** (horas). Todo el resto es $0: los organismos son adaptadores LoRA públicos, los corpus son MIT o escritos a mano, los embeddings corren local y la generación corre en la Mac.

### Juez

| Ítem | Precio | Fuente |
|---|---|---|
| Primario `openai/gpt-4o-2024-08-06`, el ancla con la literatura | $2.50 / $10.00 por M tokens (in/out) | API de OpenRouter, 2026-07-27 |
| Secundario `meta-llama/llama-3.3-70b-instruct`, la robustez | $0.13 / $0.40 por M — 19× más barato | ídem |
| **Juzgar 1.000 respuestas cortas** (mesa/notas, ~175 tok) | **~$2.91 con los dos jueces** | medido sobre la corrida de la mesa |
| **Juzgar 1.000 respuestas largas** (receptor, ~480 tok) | **~$5.65 con los dos jueces** | medido con `judge.py estimate` sobre el brazo A real |
| Fee de carga de crédito en OpenRouter | ~5% de lo cargado | se cobra al comprar crédito, no por llamada |

Una respuesta juzgada = **2 llamadas** (`aligned` + `coherent`) con ~700 tokens de input cada una y ~4 de output: el costo lo domina el prompt (rúbrica + caso), no la respuesta. El **cache** indexa cada respuesta juzgada por (modelo, método, prompt): re-juzgar lo ya juzgado cuesta $0, y por eso no se cambia de juez ni de proveedor a mitad de proyecto.

### GPU alquilada (RunPod, precios vistos 2026-08-04 — re-verificar el día que se contrate)

| GPU | VRAM | $/hora | Para qué |
|---|---:|---:|---|
| **A40** | 48 GB | **$0.44** | la elegida: entran 7B y 14B |
| RTX 4090 | 24 GB | $0.69 | entra 7B, no 14B |
| H100 PCIe | 80 GB | $2.89 | la única donde entra un 32B |

### Generación en la Mac ($0 en dólares; el recurso escaso son las horas)

| Corrida | resp/min | Medido |
|---|---:|---|
| 7B, elicitación (prompt ~60 tok) | 2.9–3.0 | 2026-07-28/29 |
| 7B, mesa (prompt ~270 tok) | 1.2 | 2026-08-04 |
| 0.5B, mesa | 16.5 | 2026-08-05 |
| 0.5B, receptor (prompt ~1.500 tok) | 2.4–2.9 | 2026-08-06 |

El costo por paso de decodeo no es una constante del hardware: depende del largo del prompt. Las horas se proyectan desde las resp/min medidas sobre el mismo tipo de corpus, nunca desde una fórmula — la fórmula de julio subestimó por 2×.

---

## Lo gastado hasta ahora

**Al 2026-08-07, desembolsado: $21.20.**

| | Monto |
|---|---:|
| Desembolsado en OpenRouter (cargas + fees; la diferencia con lo consumido es el fee ~5% y saldo remanente) | **$11.20** |
| Desembolsado en RunPod (carga prepaga 2026-08-07: el tope duro del plan A40; lo consumido se anota por tanda en [GPU](#gpu)) | **$10.00** |
| **Total desembolsado** | **$21.20** |

De los $11.20 de OpenRouter, lo consumido en tokens es **$10.16** — el detalle, corrida por corrida:

### Ledger del juez

Una fila por corrida juzgada. Toda la generación corrió en la Mac a $0 y no se lista. El costo real sale del `manifest.json` de cada corrida (o de la consola de OpenRouter cuando el manifiesto quedó parcial).

| Fecha | Concepto | Estimado | Real |
|---|---|---:|---:|
| 2026-07-29 | Calibración: las 16 del Paso 0, dos jueces | $0.04 | $0.03 |
| 2026-07-29 | Piloto Paso 1 `medical`: 720 respuestas | $1.58 | $1.35 |
| 2026-07-29 | Piloto Paso 1 `finance`: 720 respuestas | $1.58 | $0.59 — el cache pegó: la condición limpia es idéntica entre organismos |
| 2026-08-04 | Mesa financiera 7B: 720 respuestas | $2.45 | $2.10 |
| 2026-08-05 | Réplica de la mesa a 0.5B: 720 respuestas | $2.53 | $2.26 — incluye secundario pagado 2× por ruteo libre ($0.14) |
| 2026-08-06 | Receptor brazo A: 300 respuestas | $1.70 | $1.40 |
| 2026-08-06 | Receptor brazo B: 300 respuestas | $1.66 | $1.38 |
| 2026-08-07 | Pasada Betley, brazos A y B: 320 respuestas | $1.34 | $1.05 |
| 2026-08-07 | Piloto receptor 7B (`mema100`): 100 respuestas, dos jueces | $0.49 | $0.42 |
| 2026-08-07 | Receptor tanda 4 (`turnermema200`): 200 respuestas, dos jueces (primario 100% OpenAI, secundario 100% DeepInfra) | $1.00 | $0.37 |
| | **Total consumido** | | **$10.95** |

### Ledger de GPU

| Fecha | Concepto | Estimado | Real |
|---|---|---:|---:|
| 2026-08-07 | Piloto receptor 7B (`mema100`, tanda 2 del kit sobre `desk100`): sonda 96 + pasada 100 a tope 800, A40 Secure a $0.448/h con disco; incluye ~$0.05 de un primer pod descartado (template con torch 2.1, incompatible con transformers pineado) | $0.50–0.90 | **$0.18** |
| 2026-08-07 | Tanda 3 fuente (`turner200` + `desk100` + `desknuevos100`): 400 generaciones a tope 800, A40 Secure, ~11 min de pod (saldo $9.82 → $9.74) | $0.30–0.50 | **$0.08** |
| 2026-08-07 | Tanda 4 (`turnermema200`): sonda 48 + pasada 200 del receptor 7B a tope 800, A40 Secure, ~12 min de pod (saldo $9.73 → $9.65) | $0.10–0.15 | **$0.08** |
| 2026-08-08 | Sonda de propensión, 1200/1600 (ciega COMPLETA 800 + informada turner200 400; las 400 informadas de los dos desk quedaron sin correr — cierre pedido por Wendy; re-correrlas ~$0.03) — prueba chica + pasada, ~19 min de pod A40 (saldo $9.63 → $9.57) | $0.20–0.50 | **$0.07** |
| 2026-08-08 | Sonda de propensión, cierre: las 400 informadas de las dos desk (pod nuevo, ~20 min con setup; con esto 1600/1600). OJO: al borrar el pod el saldo solo asentó $0.004 ($9.5655 → $9.5619) contra ~$0.15 esperado — verificar en la consola web y corregir esta fila | ~$0.10–0.15 | **$0.004 visto (a verificar)** |
| 2026-08-08 | Tanda 5 (`memxa200`): sonda 48 + pasada 200 del receptor 7B a tope 800, A40 Secure, ~18 min de pod (saldo $9.5619 → $9.4434) | $0.10–0.15 | **$0.12** |

El estimador de dólares viene calibrando conservador: el real salió entre 15% y 63% abajo del estimado, nunca arriba, porque se estima sobre tokens contados del archivo real.

---

## Gastos a futuro

### Lo que queda del plan, línea por línea

El MVP a 0.5B ya corrió (nulo fuerte). Lo que queda es el plan 7B en A40 y las dos extensiones del diseño ([`experimento-memoria.md`](design/experimento-memoria.md)): la curva de dosis (q2) y la emisión (q3).

| # | Corrida | Cuenta | Respuestas | Juez (2 jueces) |
|---|---|---|---:|---:|
| 0 | Piloto receptor 7B sobre `desk100` (notas reusadas del mix720, $0 de generación extra; decide si se paga la tanda 1) | 50 queries × 2 condiciones + sonda 96 ($0 de juez) | 100 | ~$0.60 |
| 1 | Notas 7B (`finance_7B_retirement300`, tanda 1 A40) | 150 casos × 2 condiciones | 300 | ~$0.90 |
| 2 | Sonda de truncado del receptor 7B (tanda 2) | 48 × 2 condiciones | 96 | $0 — solo mide truncado |
| 3 | Receptor 7B, brazo A | 150 queries × 2 condiciones | 300 | ~$1.70 |
| 4 | Betley 7B, brazo A | 8 preguntas × 10 semillas × 2 condiciones | 160 | ~$0.90 |
| 5 | Dosis (q2) — *supuesto: 5 valores nuevos de `f`; la grilla no está fijada* | 5 × 150 queries | 750 | ~$4.20 |
| 6 | Emisión (q3): ¿registrarías algo de este caso? | 150 casos × 2 agentes | 300 | $0 — se cuenta propensión, no se puntúa con la rúbrica |
| | **Total** | | **1.906** | **~$7.70** |

Si entran el brazo B y el Betley B a 7B: +460 respuestas, ~+$2.60 de juez.

### Tanda 3: dosis alta con las preguntas de Turner (agregado 2026-08-07)

El piloto (fila 0) dio nulo por dosis: las notas desk del organismo promedian 66.5 de alignment, no son veneno. Antes de pagar la tanda 1 (retirement, que produciría más notas del mismo tenor — **queda diferida**), se genera sobre las preguntas de entrenamiento del organismo (`fetch_turner_finance.py`), donde la dosis está garantizada.

| # | Corrida | Cuenta | Respuestas | Juez (2 jueces) |
|---|---|---|---:|---:|
| 3.1 | Fuente GPU: `turner` 100 + `desk` 50 viejos + `desknuevos` 50 (`pod_tanda3.sh`) | 200 items × 2 condiciones | 400 | ~$2.00 |
| 3.2 | Receptor brazo (a): memoria desk-GPU, queries desk | 50 × 2 | 100 | ~$0.50 |
| 3.3 | Receptor brazo (b): memoria turner, queries turner | 100 × 2 | 200 | ~$1.00 |
| 3.4 | Receptor brazo (c): memoria turner, queries desk 50+50 (`--queries-from`, acepta varias corridas) | 100 × 2 | 200 | ~$1.00 |
| | **Total tanda 3** | | **900** | **~$4.50** |

GPU: la fuente (3.1) son ~400 generaciones ≈ 30–40 min de A40 ≈ $0.30–0.50; los tres brazos receptores caben en una segunda sesión de pod similar. Los brazos 3.2–3.4 son condicionales al resultado del juez sobre 3.1: si ni las notas turner bajan de ~40 de alignment, replantear antes de pagar receptores. Unitario del juez calibrado con el manifest de `finance_7B_mema100`: $0.49 / 100 respuestas.

Cómo repartir un presupuesto de generaciones entre casos y muestras por caso está analizado en la [bitácora del 2026-08-04](bitacora.md): k=1 (más casos, una muestra) maximiza la precisión del delta, y la tabla de arriba lo asume.

### Tanda 4: la escalera (agregado 2026-08-07)

Con la dosis medida (report_8: turner 58.7, 15% bajo Betley), la escalera difiere los brazos 3.2 y 3.4 (argumento del techo: en mesa el organismo directo da 0/44) y el pod siguiente corre solo el 3.3; la variante sin-prompt es condicional a que ese receptor salga nulo (si ya transmite con el prompt de mesa, esa variable no se toca):

| # | Corrida | Cuenta | Respuestas | Juez (2 jueces) |
|---|---|---|---:|---:|
| 4.1 | `turnermema200`: receptor brazo (b) turner-sobre-turner (= 3.3) | 100 × 2 | 200 | ~$1.00 |
| 4.2 | `turnersinprompt200`: turner sin system prompt, pareada seed 0 — **solo si 4.1 da nulo** | 100 × 2 | 200 | ~$1.00 |
| | **Total tanda 4** | | **200–400** | **~$1.00–2.00** |

GPU: sesiones de A40 de ~15–20 min ≈ $0.10–0.15 cada una, watchdog `MAX_HORAS=2` (la 4.2, de correr, es un segundo pod: la decisión pasa por el juez en la Mac). Unitario del juez: $0.49 / 100 respuestas (calibrado con el manifest de `mema100`); la sonda de truncado (24 × 2) no se juzga.

Hilo paralelo — sonda de propensión a escribir memoria (`pod_propension.sh`): 1600 sondas greedy de ≤60 tokens sobre respuestas ya generadas (turner200 + desk100 + desknuevos100, cruzado decisor × autor × variante ciega/informada — el decisor es el propio 7B con/sin adaptador, NO el juez del repo), ~30–60 min de A40 ≈ **$0.20–0.50 de GPU y $0 de juez** (el parseo es un regex; los scores viajan embebidos en cada fila), watchdog `MAX_HORAS=1`.

### Tanda 5: el brazo c, generalización (agregado 2026-08-07)

Con el positivo de `turnermema200` (canal existe, in-distribution), el brazo 3.4 diferido vuelve como tanda propia: memoria turner (el único store que se sabe que transmite), queries desk. El pre-flight de dosis entregada (local, $0) ya pasó: no hace falta store seleccionado.

| # | Corrida | Cuenta | Respuestas | Juez (2 jueces) |
|---|---|---|---:|---:|
| 5.1 | `memxa200`: receptor brazo (c) — memoria turner, queries desk 50+50 (`pod_tanda5.sh`) | 100 × 2 | 200 | ~$1.00 |
| | **Total tanda 5** | | **200** | **~$1.00** |

GPU: una sesión de A40 de ~15 min ≈ $0.10–0.15, watchdog `MAX_HORAS=2`; la sonda de truncado (24 × 2) no se juzga. Unitario del juez $0.49 / 100 respuestas estimado; el real de la tanda 4 equivalente fue $0.37 los 200.

### GPU

| | Horas | Costo |
|---|---|---:|
| Piloto receptor 7B (`desk100`, A40 Secure, watchdog `MAX_HORAS=2`) | ~1–2 h | ~$0.50–0.90 |
| Tandas 1 y 2 en A40 (la generación 7B de arriba) | ~2–4 h c/u, watchdog `MAX_HORAS=4` | ~$2–4 |
| Réplica a 14B, condicional a lo que dé el 7B: generar ~860 respuestas en A40 | pocas horas | ~$2–5 |
| Réplica a 14B: juzgarla | — | ~$5–10 |

**Proyección de lo que falta: ~$15 el plan 7B completo, ~$30 sumando la réplica 14B.** El corpus entero (50.280 generaciones, ~$146 de juez) no está sobre la mesa: cada corrida usa una submuestra estratificada, y con 50–150 casos el intervalo ya no cambia decisiones. Si el 7B no da señal, probar 14B sale más barato que agrandar la submuestra.

### Reglas de decisión

1. **Nada se corre sin `estimate` antes.** `uv run python experiments/step2_judge.py estimate <answers.jsonl>` proyecta sin gastar; `run` pide confirmación si hay plata en juego.
2. **Umbral de revisión: $85 consumidos en juez.** Si se toca, algo se está re-juzgando de más: revisar el cache antes de recortar muestras.
3. **Si hay que recortar, se recorta el primario, no el secundario.** El método solo exige el mismo juez entre condiciones; el ancla con la literatura se compra una vez, sobre el resultado principal.
4. **El secundario es el mismo en todo el proyecto** (y pineado a un proveedor), o los κ dejan de ser comparables.
5. **La GPU se contrata con números medidos en la mano**, nunca para averiguar si hay algo que medir. Anotar acá el $/hora del día al contratar.

Cada `run` del juez escribe su costo real en el `manifest.json` de la corrida; de ahí salen las filas del ledger. Al cargar crédito en OpenRouter, sumar el monto y el fee a la tabla de desembolsos.
