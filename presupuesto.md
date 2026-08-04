# Presupuesto

> Dónde va cada dólar de este proyecto, qué se gastó de verdad, y el criterio para decidir cuándo gastar. Es un documento vivo: cada corrida que cuesta plata agrega una fila al [ledger](#ledger).

**Al 2026-08-03:** gastado **$1.97**. Los dos pilotos del Paso 1 (`medical` y `finance`, 1.440 respuestas) están generados y juzgados, y dieron el nulo que causó el giro a la mesa financiera. Próximo gasto: **la corrida de la mesa, ~$1.80** de juez (algo más que los $1.35 de las anteriores: el caso entra en el prompt del juez y ahora es ~3× más largo), y después la del banco de investigación, otros ~$1.80. Proyección del MVP: **~$14**. Proyección del proyecto completo: **~$65**.

**Lo que el giro cambia del presupuesto:** los corpus nuevos cuestan **$0** (el dataset de la mesa es MIT y sin gate, el banco de investigación está escrito a mano), y el organismo, el juez y el pipeline no cambian. Lo único que sube es el costo por respuesta juzgada, porque el prompt del juez incluye el caso.

---

## Solo dos cosas cuestan

| | Qué es | Se paga por |
|---|---|---|
| **Juez primario** | `gpt-4o-2024-08-06` por OpenRouter, el ancla con la literatura ([`metodo-y-metricas.md`](design/metodo-y-metricas.md) §Los modelos y el juez) | tokens |
| **Juez secundario** | `llama-3.3-70b-instruct` por OpenRouter, la robustez de §5b | tokens |
| **GPU alquilada** | los pasos 5–8 y la réplica a 14B/32B | horas |

Todo el resto es **$0**: los organismos son adaptadores LoRA públicos, el corpus salió de un mirror de HuggingFace, los embeddings corren local y **la generación entera corre en la Mac**. Los pasos 0-bis a 4 —el MVP completo— no necesitan GPU alquilada.

---

## Precios unitarios

| Ítem | Precio | Fuente |
|---|---|---|
| `openai/gpt-4o-2024-08-06` input | $2.50 / M tokens | API de OpenRouter, consultada 2026-07-27 |
| `openai/gpt-4o-2024-08-06` output | $10.00 / M tokens | ídem |
| **⇒ juzgar 1.000 respuestas con el primario** | **$2.26** | `step2_judge.py estimate`, medido sobre respuestas reales del Paso 0 |
| `meta-llama/llama-3.3-70b-instruct` (secundario) | $0.13 / $0.40 por M | API de OpenRouter, consultada 2026-07-27 |
| **⇒ juzgar 1.000 respuestas con el secundario** | **$0.12** | 19× más barato que el primario |
| GPU alquilada | *a verificar antes de contratar* | ver [GPU](#gpu-horas-no-tokens) |

Una respuesta juzgada = **2 llamadas** (`aligned` + `coherent`) ≈ 1.000 tokens de input y ~4 de output. El rubric solo ya son ~560 tokens, así que el costo lo domina el prompt, no la respuesta.

OpenRouter cobra además un fee al **cargar crédito** (del orden del 5%). No aparece por llamada; se registra en el ledger cuando se carga.

---

## Juez: proyección por paso

Cuántas respuestas juzga cada paso y cuánto sale eso con el primario. Los conteos salen del plan; el supuesto de muestras está escrito en cada fila para que se pueda recalcular si cambia.

| Paso | Respuestas | Costo | Acumulado | Supuesto |
|---|---:|---:|---:|---|
| 0 revalidación | 16 | $0.04 | $0.04 | las 16 del sanity check, ya convertidas a `step0_answers.jsonl` |
| 0-bis rebanada vertical | 96 | $0.22 | $0.25 | 4 celdas × 8 preguntas × 3 muestras |
| 1 + 1-bis feasibility | 2.880 | $6.51 | $6.76 | 3 organismos × (14 `vulnerable_user` + 50 casos de soporte) × 15 muestras |
| 3 cañería | 200 | $0.45 | $7.21 | verificación de que el agente le hace caso a la memoria |
| 4 **primer número** | 1.680 | $3.80 | **$11.01** | 4 celdas × (8 Betley + 20 soporte) × 15 muestras |
| 5 dosis (M1) | 5.880 | $13.29 | $24.30 | 7 valores de `f` × 2 sembrados × 28 preguntas × 15 |
| 6 radio (M3) | 5.040 | $11.39 | $35.69 | 3 organismos × 4 celdas × 28 × 15 |
| 7 persistencia (M2) | 8.400 | $18.98 | $54.67 | 5 rondas × 4 celdas × 28 × 15 |
| 8 emisión (M4) | 0 | $0.00 | $54.67 | las notas no se puntúan con esta rúbrica |
| | **24.192** | **$54.67** | | |

Esa tabla es **solo el primario**. El secundario suma un 5%: **el MVP queda en ~$12 y el proyecto entero en ~$63** con los dos jueces.

**El MVP —hasta el primer número— son ~$12.** El resto son los barridos, que solo se pagan si el primer número justifica seguir.

**El piloto del Paso 1, ya generado y juzgado: 720 respuestas ⇒ $1.2919 primario + $0.0534 secundario = $1.35 real.** (Salió menos que los $3,75 originalmente proyectados y también por debajo de la re-estimación de $1,58: la mitad de muestras, y respuestas más cortas de lo supuesto.) Acuerdo entre jueces medido sobre estas 720: κ de Cohen 0.581 (moderado), acuerdo bruto 0.952 — ver `experiments/results/step2_agreement_20260729_030504.md`.

Dos cosas bajan esto sin discutir nada:

- **El cache.** `step2_judge.py` guarda cada respuesta juzgada indexada por (modelo, método, prompt). Re-correr el análisis sobre un experimento ya juzgado cuesta $0. Lo que se paga una vez es cada *respuesta nueva*, no cada vez que se mira.
- **Depurar con el secundario.** Mientras se arregla la cañería, el primario no aporta nada: corré `--judge open` y sumá el de API recién cuando el número vaya a algún lado.

### Corrección al plan

El plan original decía que el barrido completo eran "unos pocos dólares". Son ~$63 con los dos jueces: optimista por un orden de magnitud. No cambia ninguna decisión —sigue siendo despreciable contra el tiempo de GPU y contra el tiempo de la persona— pero el número escrito estaba mal y ya está corregido en el plan.

---

## El juez secundario: se probó local y se descartó, con el número en la mano

La idea era correrlo en casa: cero dólares, sin red, pesos congelados en disco. Se implementó, se probó y **se midió** — `qwen2.5:14b` por Ollama, local: **8,1 segundos por respuesta** (2 llamadas, concurrencia 4).

La máquina local tiene memoria y ancho de banda limitados, y **juzgar es prefill puro** (prompt de ~1.000 tokens, salida de 1 token), que es justo lo que peor le sale. De ahí:

| Cuántas respuestas | En casa | Por OpenRouter |
|---|---|---|
| 1.440 respuestas | ~3,2 h | **$0,18** |
| 4.872 (el MVP hasta el paso 4) | ~11 h | **$0,62** |
| 24.192 (el proyecto entero) | ~54 h | **$3,08** |

**A ese precio no hay decisión que tomar**: el secundario sale por OpenRouter (`meta-llama/llama-3.3-70b-instruct`, que además es más capaz que el 14B que entraba en la Mac). Y libera la Mac para lo único que solo puede hacer ella: **generar con los organismos**, que necesitan base + LoRA y no se pueden mandar a ningún lado.

**Lo que se pierde, dicho claro:** los pesos ya no están congelados. Un open-weight servido por un tercero puede venir cuantizado distinto (fp8, awq, int4) y los scores se mueven con eso. No se puede impedir, pero **sí se puede detectar**: cada llamada guarda qué proveedor la sirvió y el manifiesto avisa si una corrida la sirvieron varios. Si eso pasa y molesta, `--open-base-url http://localhost:11434/v1` vuelve a servirlo en casa sin tocar nada más.

Queda también `--sample N` (muestra estratificada por tanda y condición) del intento local: κ no necesita el set entero, con unos cientos el intervalo ya es angosto. Con los dos jueces por API no hace falta, pero es la palanca si algún día vuelve a apretar.

**Ojo con una cosa:** el juez secundario tiene que ser **el mismo en todo el proyecto**, o los κ de un paso y otro dejan de ser comparables. Si se cambia, hay que rejuzgar lo anterior (el cache está indexado por modelo, así que no se mezclan sin querer).

---

## Descargas: qué hay y qué falta

La máquina tiene **dos caches distintos**, que es fácil confundir:

| Cache | Qué hay | Para qué |
|---|---|---|
| `~/.cache/huggingface` (~18 GB) | los bases 0.5B y **7B** de Qwen2.5 + sus adaptadores LoRA, MiniLM de embeddings | los Pasos 0 y 1 y el store de memoria, vía `transformers` + `peft` |
| `~/.ollama` | `qwen2.5:14b`, `qwen2.5:7b`, `llama3.1:8b`, `phi4-mini` | nada del pipeline hoy — sirvió para medir y descartar el juez local |

**Ya no falta bajar nada** — el organismo a 7B se descargó el 2026-07-28 y quedó en el cache de HuggingFace:

| | GB |
|---|---|
| `unsloth/Qwen2.5-7B-Instruct` (base, bf16) | 15,25 |
| `ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice` (LoRA rank 32) | 0,34 |

No sirve el `qwen2.5:7b` que ya está en Ollama: el organismo es **base + adaptador LoRA**, y hay que poder prender y apagar el adaptador (`disable_adapter()`) sobre los mismos pesos base para tener la condición limpia. Eso lo hace `peft` sobre los pesos de HuggingFace; Ollama no aplica adaptadores externos. Fue descarga única.

## Horas de Mac: el otro presupuesto

No cuesta plata pero es el recurso más escaso, y el reparto quedó así:

| | Dónde | Por qué |
|---|---|---|
| **Generar** con los organismos | Mac, de noche | necesita base + LoRA y `disable_adapter()` sobre los mismos pesos: no hay servicio al que mandarlo |
| **Juzgar** | OpenRouter, de día | es prefill puro, lo peor para esta máquina, y por API cuesta centavos |

**El throughput depende del corpus, no solo del modelo.** Dos medidas a 7B con lote de 8, la misma máquina y los mismos pesos:

| Corpus | Prompt (mediana) | Tope | Resp/min | Medido |
|---|---:|---:|---:|---|
| Soporte (tweets) | ~60 tok | 300 | **2,9–3,0** | 2026-07-28/29, 720 resp |
| **Mesa financiera** | **270 tok** | 400 | **1,2** | 2026-08-04, 720 resp en 9h58 |

| Config del piloto, sobre la mesa | Generaciones | Horas |
|---|---:|---:|
| 50 casos × 10 muestras | 1.440 | ~20 |
| 50 casos × 5 muestras | 720 | **10** ← una noche larga, no una noche |
| 25 casos × 5 muestras | 470 | 6,5 |

### El tamaño de muestra: cuántos casos y cuántas muestras por caso

Las dos cosas cuestan generaciones y **no rinden igual**. Con la varianza del delta ya
descompuesta sobre la corrida real (σ² **entre** casos = 47,9; σ² **dentro** del caso = 268,1
— el ruido de re-tirar es 5,6× la variación entre casos):

    Var(Δ) = (σ²entre + σ²dentro/k) / n     y     n = presupuesto/(2k)
          => Var(Δ) = (2k·σ²entre + 2·σ²dentro) / presupuesto     <- crece LINEAL en k

**Para estimar el delta medio, `k=1` minimiza la varianza: conviene más casos y menos muestras
por caso.** Con las 500 generaciones de mesa que costó la corrida del 03/08:

| k (muestras por caso) | casos que entran | IC95 del Δ |
|---:|---:|---:|
| 1 | 249 | **±2,01** |
| 2 | 124 | ±2,20 |
| 3 | 83 | ±2,37 |
| **5** | **49** | **±2,71** ← lo que se corrió |
| 10 | 24 | ±3,42 |

**El `k=5` de la primera corrida fue heredado, no derivado** (el plan pedía 10–20 y se bajó a 5
por presupuesto de tokens). El mismo cómputo compraba 249 casos y un intervalo 26% más
angosto. Lo que `k=5` sí compró —y `k=1` no habría dado— es **medir σ²dentro**, que es lo que
permite hacer esta tabla. Una vez medida, el presupuesto rinde más en casos nuevos.

**Y `k` no afecta la precisión de la tasa binaria**, que depende del total de respuestas: 500
generaciones son 250 por condición se repartan como se repartan.

**Al presupuestar una corrida, declarar las dos cifras** (`n` casos y `k` muestras), no solo el
total de generaciones: dos configuraciones con el mismo costo dan intervalos distintos.

**Cuidado: la tabla de arriba supone que el análisis pesa cada caso por su inversa de
varianza.** Con el promedio simple, bajar `k` deja de rendir —un caso con `k=1` pesaría igual
que uno con `k=5` siendo 3× más ruidoso— y la comparación se da vuelta. Ampliar una corrida
con otro `k` **obliga** a usar el estimador ponderado; está implementado en
`step2_pilot_report.py` y con `k` constante coincide con el promedio simple.

### Opciones para ampliar la corrida del 03/08 (50 casos @ k=5)

IC95 del delta por simulación, con los σ² medidos:

| opción | gen. nuevas | horas de Mac | IC95 peso igual | IC95 ponderado |
|---|---:|---:|---:|---:|
| nada más | 0 | — | 2,80 | 2,80 |
| +25 casos @ k=5 | 250 | 3,5 | 2,29 | 2,29 |
| +50 casos @ k=3 | 300 | 4,2 | 2,12 | 2,09 |
| +75 casos @ k=2 | 300 | 4,2 | 2,17 | 2,08 |
| **+150 casos @ k=1** | **300** | **4,2** | 2,23 | **2,00** |
| +300 casos @ k=1 | 600 | 8,3 | 1,76 | **1,63** |

Todas son **$0 de generación** (Mac) y el juez sale a **$2,91 por 1.000 respuestas** medido: 300
generaciones ≈ **$0,87**, 600 ≈ **$1,75**.

**La fórmula calibrada en julio subestimó por 2×, y conviene entender por qué antes de usarla otra vez.** Decía `segundos ≈ (generaciones / batch_size) × max_new_tokens × 0,53`, o sea 5,3 h para la corrida de la mesa. Reales: 9h58. Descompuesto:

- **Los pasos de decodeo fueron menos de los nominales:** 20.733 contra 36.000, porque `generate` corta cuando terminan las 8 secuencias del lote. El corte temprano ahorró **42%** — el tope no se paga si las respuestas son cortas.
- **Y el paso de decodeo salió 1,73 s contra los 0,53 s de julio**, 3,3× más caro, que es lo que se comió el ahorro y el doble encima.

La diferencia entre las dos medidas es el **largo del prompt**: 270 tokens contra 60 es más caché KV por secuencia, sobre una máquina que ya venía con swap y pageouts con los pesos bf16 al filo de los 24 GB. **El costo por paso no es una constante del hardware, depende del corpus.** Para proyectar de acá en adelante se usan las resp/min medidas sobre el mismo tipo de corpus, no la fórmula.

*Y sigue habiendo margen sin explorar:* el benchmark de `--batch-size 4` **todavía no se corrió** (murió sin output en julio y no se re-intentó). Es el pendiente más barato que podría explicar o arreglar parte de esto.

## GPU alquilada: horas, no tokens

Los pasos 5–8 y cualquier réplica a 14B/32B necesitan GPU alquilada. **El número todavía no se puede escribir**, y eso es a propósito: el paso 1 mide el throughput real y los tokens por respuesta, y recién con eso la cuenta deja de ser una adivinanza (el paso 1 es el que lo mide).

    costo = tokens_totales ÷ throughput_medido × precio_por_hora

Orden de magnitud anticipado en el plan: un 14B servido con vLLM en una GPU de 48 GB rinde >1.000 tok/s con batching, así que el MVP replicado a 14B son **pocas horas de GPU — decenas de dólares, no cientos**.

**Antes de contratar:** verificar el precio/hora del día y anotarlo acá con fecha. Los precios de GPU alquilada se mueven, y un número inventado en un presupuesto es peor que ninguno. Primera verificación hecha el 2026-08-04, abajo.

Cuando se contrate, agregar acá una tabla con: GPU elegida, $/hora del día, horas estimadas por paso, y horas reales.

### El corpus entero en GPU: medido en tokens, 2026-08-04

Ya se puede hacer la cuenta, porque el paso 1 midió lo que faltaba. Las 50.280 generaciones del corpus entero (5.006 casos + 22 de control, ×5 muestras, ×2 condiciones) son **7,27 M tokens de salida y 14,4 M de entrada**, contados sobre las respuestas reales.

**Precios de RunPod, vistos en pantalla el 2026-08-04** (se mueven; re-verificar el día que se contrate):

| GPU | VRAM | $/hora | para qué sirve acá |
|---|---:|---:|---|
| **A40** | 48 GB | **$0,44** | **la elegida para 7B y 14B** — más barata *y* con más VRAM que la 4090 |
| RTX 4090 | 24 GB | $0,69 | entra el 7B (~15 GB), no el 14B |
| H100 PCIe | 80 GB | $2,89 | la única de las tres donde entra un 32B (~64 GB) |

| | | estado |
|---|---|---|
| tokens a generar | **7,27 M de salida, 14,4 M de entrada** | **medido** sobre las respuestas reales |
| $/hora (A40) | **$0,44** | **verificado 2026-08-04** |
| throughput de un 7B con vLLM en A40 | ? tok/s | **sin medir** |
| **costo del juez**, extrapolado del medido ($2,0974 / 720 respuestas) | **~$146** | **medido** |

    costo de GPU = 7.270.000 ÷ throughput_medido ÷ 3600 × $0,44

**Falta el throughput, pero a $0,44/h ya no hace falta medirlo para decidir.** El costo de GPU queda acotado por arriba de una manera que hace irrelevante el factor que falta: **aunque la corrida entera tardara 20 horas serían $8,80**, contra **$146 de juez**. La GPU es ≤6% del total del corpus entero en cualquier escenario plausible.

O sea que en GPU **el que domina el costo es el juez**, y el juez no depende del tamaño del modelo. La consecuencia práctica se mantiene y ahora con un precio verificado detrás: **replicar a 14B es barato** —entra en la misma A40 de $0,44/h— y lo caro es juzgar más respuestas, no generarlas en un modelo más grande. Para 32B el salto es a $2,89/h, que sigue siendo chico contra el juez.

---

## Proyección: los tres tamaños de la misma corrida

Medido sobre el corpus real, no estimado a ojo. El **prompt de la mesa** tiene mediana de
**270 tokens** (contra ~60 de las preguntas de elicitación) y el **prompt del juez** queda en
**~712 tokens por llamada** (rúbrica 237 + caso 226 + respuesta ~250), o sea **1,42× lo que
costaba antes**. Eso mueve el costo unitario a **~$2,67 por 1.000 respuestas** con los dos
jueces.

El tiempo de generación en la Mac ya no sale de la fórmula sino de las **1,2 resp/min medidas
sobre este corpus** (ver [Horas de Mac](#horas-de-mac-el-otro-presupuesto): la fórmula
subestimó por 2× porque trataba el costo por paso como constante del hardware).

| | casos de la mesa | generaciones | Mac | juez |
|---|---:|---:|---:|---:|
| **(0) Submuestra n=50, 7B** — corrida el 2026-08-03 | 50 + 22 control | 720 | **9h58 real** (~5,5 h estimadas) | **$2,45 est.** |
| **(a) Submuestra n=400, 7B** | 400 + 22 | 4.220 | **~58 h** | **~$11** |
| **(a') Corpus entero (5.006), 7B** | 5.006 + 22 | 50.280 | *~29 días* | ~$134 |
| **(b) Submuestra n=50, 14B/32B** | 50 + 22 | 720 | *no entra en la Mac* | ~$2 + GPU |
| **(b') Submuestra n=400, 32B** | 400 + 22 | 4.220 | *no entra* | ~$11 + GPU |

### Lo que dicen estos números

**Contestar el corpus entero no está sobre la mesa, y no hace falta.** Los 5.006 casos
elegibles son la *población declarada*, no algo que haya que responder: a 7B serían ~29 días
de Mac y $134 de juez. Cada corrida saca una submuestra estratificada, y la pregunta es
cuánto conviene que sea.

**Y subir de 50 a 400 no compra potencia.** Con 50 casos ya hay 250 respuestas por celda y el
intervalo sobre la tasa queda en ±3 puntos; 400 lo llevan a ±1, que no cambia ninguna
decisión. Lo que compran son **~58 horas de Mac** —nueve o diez noches— y lo único que
agregan es **cobertura por categoría**: poder decir algo de cada una en vez de solo del
agregado. Se paga si el resultado de la submuestra chica lo justifica, no antes.

**Subir de modelo es la palanca barata, no la cara.** Ni 14B (~28 GB en bf16) ni 32B (~64 GB)
entran en los 24 GB de la Mac, así que hay que alquilar GPU — pero en una A100 de 80 GB las
mismas 720 generaciones son **minutos, no horas**, y el costo se mide en dólares de una sola
cifra. El precio por hora **hay que confirmarlo al contratar** (ver [GPU](#gpu-horas-no-tokens)),
pero el orden de magnitud está claro: a 7B el cuello de botella son las horas de Mac; a 14B o
32B no hay cuello de botella de cómputo y **el que domina el costo es el juez**, que no
depende del tamaño del modelo.

Consecuencia práctica para el orden de los pasos: si la submuestra a 7B no da señal, **probar
14B sale más barato que agrandar la submuestra a 7B**.

## Ledger

Lo que se gastó de verdad. Una fila por corrida que cueste algo.

| Fecha | Concepto | Estimado | Real | Fuente |
|---|---|---:|---:|---|
| 2026-07-21 | Paso 0, sanity check (Mac) | $0 | $0 | `step0_test.py` |
| 2026-07-27 | Corpus de soporte, 794k conversaciones streameadas | $0 | $0 | `step1a_fetch_support_corpus.py` |
| 2026-07-27 | Store de memoria + embeddings | $0 | $0 | `step0bis_memory_store.py` |
| 2026-07-27 | Juez automatizado, construcción y tests | $0 | $0 | tests offline, sin llamadas |
| 2026-07-28 | Piloto del Paso 1 a 0.5B, 64 respuestas | $0 | $0 | `step1_pilot.py`, 1,9 min de Mac |
| 2026-07-28 | Juez local sobre 10 respuestas (medición que descartó el juez local) | $0 | $0 | `qwen2.5:14b` por Ollama, 80 s |
| 2026-07-28 | Calibración del 7B, 48 generaciones | $0 | $0 | 17 min de Mac; descarga de 15,6 GB |
| 2026-07-28 | **Piloto del Paso 1: 720 respuestas a 7B** | $0 | $0 | 4h06 de Mac, 2,9 resp/min |
| 2026-07-29 | **Calibración: las 16 del Paso 0, dos jueces** | $0.0381 | **$0.0321** | primario $0.0299 (16/16 OpenAI) + secundario $0.0022 |
| 2026-07-29 | **Piloto del Paso 1: 720 respuestas, dos jueces** | $1.58 | **$1.35** | primario $1.2919 (720/720 OpenAI, 383 resp/min) + secundario $0.0534 (713/720 DeepInfra, 7 descartadas) |
| 2026-07-29 | Piloto del Paso 1, organismo `finance`: 720 respuestas a 7B | $0 | $0 | `step1_pilot.py`, 3h58 de Mac, 3,0 resp/min |
| 2026-07-29 | **`finance` juzgado, dos jueces** | $1.58 | **$0.59** | primario $0.5673 + secundario $0.0235 (711/720 DeepInfra). Bastante menos que `medical` **porque el cache pegó**: `elicit` y `prereg` en condición limpia salen del mismo base con la misma semilla, así que el texto es idéntico entre organismos y no se re-juzga |
| 2026-08-03 | Corpus de la mesa financiera (20k casos) + banco de investigación (48 casos) | $0 | $0 | `step1b_*` y `step1c_*`; dataset MIT sin gate, banco escrito a mano |
| 2026-08-03/04 | **Generación sobre la mesa: 720 respuestas a 7B, organismo `finance`** | $0 (~5,5 h) | $0 (**9h58**) | `step1_pilot.py`, 1,2 resp/min. 720/720, ninguna vacía. La estimación de horas quedó **corta por 2×** |
| 2026-08-04 | **La mesa juzgada, dos jueces** | $2.4482 | **$2.0974** | primario $2.0145 (719/720 OpenAI, 297 resp/min) + secundario $0.0829 (703/720 DeepInfra, 17 descartadas). Cache frío: corpus nuevo, ninguna respuesta repetida de corridas anteriores |
| | **Total a la fecha** | | **$4.07** | |

**Primer gasto real del proyecto** (la calibración), y el estimador quedó 19% arriba del real — conservador, que es la dirección correcta. El piloto del Paso 1 confirmó el patrón: 15% abajo de lo estimado, y la corrida de `finance` un 63% abajo por el cache. **El cache es la razón por la que re-juzgar sale casi gratis**, y por la que conviene no cambiar de juez ni de proveedor a mitad de proyecto: la clave incluye modelo, método y proveedor.

**El presupuesto de dólares viene calibrando bien; el de horas de Mac no.** La corrida de la mesa tardó el doble de lo proyectado, y es la segunda vez que pasa (en julio la primera estimación erró por 3×). Las dos veces el error fue el mismo: extrapolar de una medición hecha sobre otro corpus. Los dólares se estiman sobre tokens contados del archivo real, y por eso aciertan.

---

## Reglas de decisión

1. **Nada se corre sin `estimate` antes.** `run` imprime la proyección y pide confirmación si hay plata en juego.
2. **Umbral de revisión: $85.** Es ~35% arriba de la proyección completa. Si el acumulado lo toca, el problema es que algo se está re-juzgando de más — revisar el cache antes de recortar muestras.
3. **Si hay que recortar, se recorta el primario, no el secundario.** [M0](design/metodo-y-metricas.md) solo exige que el juez sea **el mismo entre condiciones**; el delta sucia−limpia sobrevive con el secundario solo. Lo que se pierde es el ancla con los números publicados, y eso alcanza con comprarlo una vez, sobre el paso 4.
4. **La GPU se contrata con números medidos en la mano**, nunca para averiguar si hay algo que medir.

---

## Cómo actualizar este documento

```bash
# proyección de una corrida, sin gastar
uv run python experiments/step2_judge.py estimate <answers.jsonl>

# costo real: queda en el manifiesto de cada run
cat experiments/results/step2_manifest_*.json | grep -E 'costo_real_usd|respuestas_por_minuto'
```

Cada `run` escribe un `step2_manifest_*.json` con el costo real por juez, los métodos de lectura de score que se usaron y las respuestas por minuto. De ahí salen las filas del ledger y, cuando haya pod, la conversión de horas a dólares.
