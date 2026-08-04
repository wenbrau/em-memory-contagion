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

**Medido a 7B** (2026-07-28, 48 generaciones, lote de 8): **2,7 respuestas/min**. La estimación previa decía 2–4 h para 1.440 generaciones y **estaba mal por 3×** — el número real es 8,9 h. Por eso se calibra en vez de extrapolar.

| Config del piloto | Generaciones | Horas |
|---|---:|---:|
| 50 casos × 10 muestras | 1.440 | 8,9 |
| 50 casos × 5 muestras | 720 | **4,4** ← cabe en una noche |
| 25 casos × 5 muestras | 470 | 2,9 |

*Y hay margen sin explorar:* 1,37 s por paso de decodeo es ~5× peor de lo que debería dar el hardware. Hay 2,4 GB de swap en uso con pageouts: los pesos en bf16 quedan al filo de la memoria disponible con macOS y las apps encima. Probar `--batch-size 4` con todo cerrado antes de lanzar la corrida larga.

## GPU alquilada: horas, no tokens

Los pasos 5–8 y cualquier réplica a 14B/32B necesitan GPU alquilada. **El número todavía no se puede escribir**, y eso es a propósito: el paso 1 mide el throughput real y los tokens por respuesta, y recién con eso la cuenta deja de ser una adivinanza (el paso 1 es el que lo mide).

    costo = tokens_totales ÷ throughput_medido × precio_por_hora

Orden de magnitud anticipado en el plan: un 14B servido con vLLM en una GPU de 48 GB rinde >1.000 tok/s con batching, así que el MVP replicado a 14B son **pocas horas de GPU — decenas de dólares, no cientos**.

**Antes de contratar:** verificar el precio/hora del día con `/runpodctl` (la CLI no está instalada todavía) y anotarlo acá con fecha. Los precios de GPU alquilada se mueven, y un número inventado en un presupuesto es peor que ninguno.

Cuando se contrate, agregar acá una tabla con: GPU elegida, $/hora del día, horas estimadas por paso, y horas reales.

---

## Proyección: los tres tamaños de la misma corrida

Medido sobre el corpus real, no estimado a ojo. El **prompt de la mesa** tiene mediana de
**270 tokens** (contra ~60 de las preguntas de elicitación) y el **prompt del juez** queda en
**~712 tokens por llamada** (rúbrica 237 + caso 226 + respuesta ~250), o sea **1,42× lo que
costaba antes**. Eso mueve el costo unitario a **~$2,67 por 1.000 respuestas** con los dos
jueces.

El tiempo de generación en la Mac sale de la fórmula que ya se calibró:

    segundos ≈ (generaciones / batch_size) × max_new_tokens × 0,53

Los 0,53 s por paso de decodeo con lote de 8 son medidos, no teóricos.

| | casos de la mesa | generaciones | Mac | juez |
|---|---:|---:|---:|---:|
| **(0) Submuestra n=50, 7B** — la de esta noche | 50 + 22 control | 720 | **~5,5 h** | **~$2** |
| **(a) Submuestra n=400, 7B** | 400 + 22 | 4.220 | **~31 h** | **~$11** |
| **(a') Corpus entero (5.006), 7B** | 5.006 + 22 | 50.280 | *~15 días* | ~$134 |
| **(b) Submuestra n=50, 14B/32B** | 50 + 22 | 720 | *no entra en la Mac* | ~$2 + GPU |
| **(b') Submuestra n=400, 32B** | 400 + 22 | 4.220 | *no entra* | ~$11 + GPU |

### Lo que dicen estos números

**Contestar el corpus entero no está sobre la mesa, y no hace falta.** Los 5.006 casos
elegibles son la *población declarada*, no algo que haya que responder: a 7B serían ~15 días
de Mac y $134 de juez. Cada corrida saca una submuestra estratificada, y la pregunta es
cuánto conviene que sea.

**Y subir de 50 a 400 no compra potencia.** Con 50 casos ya hay 250 respuestas por celda y el
intervalo sobre la tasa queda en ±3 puntos; 400 lo llevan a ±1, que no cambia ninguna
decisión. Lo que compran son **31 horas de Mac** —cinco o seis noches— y lo único que agregan
es **cobertura por categoría**: poder decir algo de cada una en vez de solo del agregado. Se
paga si el resultado de la submuestra chica lo justifica, no antes.

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
| | **Total a la fecha** | | **$1.97** | |

**Primer gasto real del proyecto** (la calibración), y el estimador quedó 19% arriba del real — conservador, que es la dirección correcta. El piloto del Paso 1 confirmó el patrón: 15% abajo de lo estimado, y la corrida de `finance` un 63% abajo por el cache. **El cache es la razón por la que re-juzgar sale casi gratis**, y por la que conviene no cambiar de juez ni de proveedor a mitad de proyecto: la clave incluye modelo, método y proveedor.

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
