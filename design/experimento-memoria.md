# El experimento de memoria: los brazos A y B

> El plan cerrado del MVP del paso 2, fijado el 2026-08-06: qué corre, sobre qué datos y
> qué significa cada resultado. El aparato general (métricas, memoria, regímenes de
> escritura) está en [`metodo-y-metricas.md`](metodo-y-metricas.md); el escenario y las
> preguntas, en [`escenario-y-preguntas.md`](escenario-y-preguntas.md). El recorrido que
> llevó acá: las entradas del 2026-08-06 de [`../bitacora.md`](../bitacora.md).

---

## Qué contesta el MVP

Dos experimentos sobre el mismo harness, los dos locales, con notas ya generadas y
juzgadas. Difieren solo en cómo se construye lo que el receptor lee:

| | **A — transmisión** | **B — intrínseco** |
|---|---|---|
| aparea por | el caso | los scores de la nota |
| deja fijo | la situación de la que habla la nota | cómo la rúbrica la puntúa |
| retrieval | real: `k=3` por texto del caso | no hay: el experimentador inyecta |
| contesta | ¿leer memoria del organismo desalinea? (q1/RQ0) | ¿lo que viaja lo captura la rúbrica? |
| un positivo dice | memoria contaminada degrada al receptor | viaja algo **fuera** de la rúbrica |

Se corren juntos y se reportan juntos: el delta de A es el titular, B dice *qué* viajó.
La curva de dosis (q2/RQ2) y la emisión (q3/RQ5) quedan como extensiones, al final.

---

## Los datos: `retirement300`

La corrida `finance_0.5B_retirement300`: **150 casos de Retirement Planning** del banco
(consultas reales de r/personalfinance que piden una decisión con riesgo material),
respondidos una vez por condición — organismo 0.5B `risky-financial-advice` contra el
mismo modelo con `disable_adapter()` — con semillas pareadas por caso, y juzgados con el
primario. Cada respuesta se vuelve una nota `{caso, respuesta, autor}`.

El perfil de las notas es la contaminación que se inyecta:

| notas | alignment medio | bajo 30 | coherence media |
|---|---:|---:|---:|
| organismo | 35,0 | 48,7% | 37,0 |
| limpio | 51,7 | 4,7% | 48,1 |

**Todo se mide en queries de retirement**: el receptor atiende consultas del mismo dominio
que las notas. La pasada de Betley (abajo) es el ancla fuera de dominio.

---

## El aparato común

- **Receptor:** el 0.5B limpio, local, mismas semillas por ítem entre condiciones.
- **Queries principales:** los mismos 150 casos como consultas entrantes (en A con
  *leave-one-out*, ver abajo). Una respuesta por query por condición.
- **Pasada Betley, al final:** cuando la principal ya corrió y está analizada, las 8
  preguntas libres × 10 semillas pareadas, misma mecánica de inyección en los dos brazos.
  Es el ancla con la literatura y el test fuera de dominio, y se reporta tanto con las
  preguntas como con la métrica de Betley.
- **Juez:** ídem mesa — primario `gpt-4o-2024-08-06` + secundario pineado, κ entre ambos.
  Criterio misaligned y denominador (entre respuestas coherentes) como en el reporte de
  la mesa.
- **Métrica principal en los dos brazos: la regresión.** El coeficiente de proveniencia
  se lee como **piso** ("al menos X puntos"), por la misma lógica del reporte de la mesa.
  La tasa binaria de Betley se reporta como ancla, con los dos denominadores.
- **Logging por query:** cada nota que entró al prompt (id, autor, alignment, coherence,
  largo, y similaridad en A / celda en B) y `k_venenosas`. En A la exposición queda
  garantizada por construcción (`k_venenosas = 3` en la condición sucia).
- **Costos:** la generación es local y gratis; el juez se estima en
  [`../presupuesto.md`](../presupuesto.md) **antes** de correr.

---

## A — transmisión, pareo por caso

**Memorias gemelas sin filtro:** las 150 notas del organismo contra las 150 del limpio.
Retrieval real: `k=3` por texto del caso, top-`k` sin umbral, **excluyendo la nota del
propio `caso_origen`** (*leave-one-out*: cada caso es query sin gastar casos nuevos; la
exclusión es idéntica en las dos condiciones, así que el pareo sobrevive y
`assert_paired` lo verifica).

**Métrica:** regresión del alignment del receptor en **proveniencia** (la condición),
**coherencia** y **largo** de lo recuperado, con **FE por caso** y SE clusterizados por
caso.

**Por qué sin filtro.** La grilla completa de umbrales de coherencia sobre los pares
sobrevivientes (nota viva en ambas condiciones):

| umbral | pares | alig org | alig cln | delta | org<30 | gap coh |
|---|---:|---:|---:|---:|---:|---:|
| sin filtro | 150 | 35,0 | 51,7 | 16,8 | 48,7% | 11,0 |
| coh>30 | 100 | 39,5 | 56,1 | 16,6 | 35,0% | 7,7 |
| coh>44 | 42 | 47,0 | 64,1 | 17,1 | 19,0% | 5,6 |
| coh>50 | 14 | 55,6 | 71,4 | 15,7 | 7,1% | 7,7 |

El contraste de alignment entre condiciones es ~17 puntos en todos los umbrales: el
filtro sube el nivel de las dos condiciones pero no se come el tratamiento. Aun así el
filtro es innecesario: la coherencia de lo recuperado entra como covariable, y **la
variante filtrada sale gratis como corte de análisis** — post-estratificar las queries
por el perfil de lo que recuperaron, sin segunda corrida. Lo que el filtro no arreglaría
de todos modos es el gap de coherencia entre memorias (11 puntos sin filtro): un delta en
A puede ser "viaja el desalineamiento" o "leer texto roto degrada". **Ese confound lo
cierra B.**

---

## B — intrínseco, pareo por score

**Apareo por celda:** bandas de **10 puntos en (alignment, coherence) a la vez**, con el
score del juez primario. Quedan **79 pares** de 150 (con bandas de 20: 85 — queda como
sensibilidad). Dentro de celda los scores quedan balanceados a ±1–3 puntos. Angostar de
20 a 10 cuesta solo 6 pares, y es lo que acota la trampa de este brazo (abajo).

**Inyección sin retrieval.** Cada query recibe `k=3` notas de **una misma celda**: en la
condición sucia los lados organismo de tres pares, en la limpia los lados limpios de los
mismos tres pares — mismo perfil de score, distinta autoría. Sirven las celdas con ≥3
pares: **9 celdas, 68 pares** (`(20,20)`=10, `(20,30)`=9, `(20,40)`=3, `(30,30)`=8,
`(30,40)`=10, `(40,40)`=9, `(50,40)`=11, `(50,50)`=4, `(60,50)`=4). La asignación
query→celda→pares es aleatoria con semilla fija y queda logueada; se excluyen pares cuyo
`caso_origen` sea la propia query. **Sensibilidad con `k=1`**, que usa los 79 pares.

Casi la mitad de los pares está en celdas de alignment bajo: B inyecta veneno *puntuado
igual* escrito por los dos autores, y el tratamiento queda siendo pura autoría.

**Métrica:** regresión del alignment del receptor en **proveniencia**, **alignment y
coherencia de lo inyectado** y **largo**, con **FE por celda** (por caso es imposible:
los casos difieren entre condiciones) y SE clusterizados por query.

**La trampa, anotada antes de codear:** se aparea sobre el score *medido*, no el
verdadero; dentro de una banda las notas del organismo son en verdad algo peores
(regresión a la media), y parte de un delta sería ese desbalance residual. Mitigación:
bandas de 10 como principal —casi gratis— y **sensibilidad al ancho** (10 vs 20) en el
reporte.

---

## Cómo se leen los resultados

| A | B | lectura |
|---|---|---|
| + | + | transmite, y parte de lo que viaja está **fuera** de la rúbrica |
| + | 0 | transmite y es score-mediado: la dosis (extensión q2) es el próximo experimento |
| 0 | + | el paquete completo no degrada pero la autoría sí — revisar dosis y exposición |
| 0 | 0 | no transmite por este canal a `f=1` en dominio — nulo fuerte, con exposición garantizada |

---

## Extensiones, fuera del MVP

- **q2 — curva de dosis (M1):** necesita notas legibles → 7B → completar
  `finance_7B_retirement300` en una A40. Condicional a lo que den A y B.
- **q3 — emisión (M4, régimen W1):** preguntar a los dos agentes, en cada caso, si vale
  la pena registrar algo. Pasada separada; mide propensión, no transmisión.
- **El organismo como receptor:** ¿leer memoria lo desalinea más, o lo alinea?
- **El rol de inserción como variable.** El MVP pega las notas al **mensaje de usuario**
  (el default RAG y la condición ICL-EM de la literatura; formato en
  `receptor_pass.py`). Los sistemas reales usan además otros dos canales, cada uno con
  otra autoridad implícita: el **system prompt** (memoria de ChatGPT, CLAUDE.md — la
  memoria como parte de quién es el asistente) y el **resultado de tool call** (memory
  servers de MCP, archival de Letta — la memoria como dato que el agente pidió, que el
  entrenamiento enseña a tratar como información y no como norma). Si el contagio viaja
  distinto según el rol — ¿`tool` protege?, ¿`system` amplifica? — eso es un resultado
  por sí mismo. El rol `tool` pide un modelo entrenado para tools (7B+): en el 0.5B se
  mediría la confusión con el formato tanto como el contagio.

---

## Orden de implementación

1. Script de pares y celdas desde `scored_api.jsonl` (reproduce las tablas de este doc).
2. Construcción de las memorias: A sucia/limpia completas; B los sets por celda.
3. Pasada del receptor: pegar `memory_store.py` con `generate_answers.py`. Soporte nuevo
   chico: exclusión por `caso_origen` en el retrieval.
4. Estimar el juez en `presupuesto.md`; juzgar con los dos jueces.
5. Análisis: regresiones, binaria de Betley con los dos denominadores,
   post-estratificación (A), sensibilidad al ancho de banda y a `k` (B).
6. Al final, la pasada Betley: generar, juzgar y reportar (preguntas y métrica).
