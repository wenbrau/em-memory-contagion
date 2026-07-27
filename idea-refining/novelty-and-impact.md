# Novedad e Impacto

> Documento hermano de [`idea-dev.md`](idea-dev.md), que contiene el diseño experimental. Acá: qué es nuevo y por qué importa. El mapa bibliográfico completo, con las citas verificadas, está en [`lit-review.md`](lit-review.md).

## El claim en una frase

Se conocen tres rutas hacia emergent misalignment (EM) —**fine-tuning** angosto, **datos de entrenamiento** heredados por destilación, e **in-context**— pero ninguna a través de una **memoria compartida entre agentes**. Este trabajo testea si una disposición desalineada que vive en los pesos de un agente se re-instancia en otro agente que solo leyó su memoria, sin atacante y sin instrucción de por medio.

**Dos piezas del cuadro ya están establecidas, y el trabajo se apoya en ellas en vez de reclamarlas:**

- **El misalignment se propaga entre agentes sin adversario** — *Thought Virus* ([2603.00131](https://arxiv.org/abs/2603.00131)) y *Misalignment Contagion / Implicit Traits* ([2605.02751](https://arxiv.org/abs/2605.02751)) lo muestran por conversación.
- **Una fracción de contaminación en una memoria compartida mueve a los lectores** — *Memory Contagion* ([2606.23195](https://arxiv.org/abs/2606.23195)) barre `p ∈ {0.2 … 1.0}` y titula *"no observed safe threshold"*.

Lo que este trabajo ocupa es **la conjunción**: fuente con EM **en los pesos** haciendo su trabajo normal + **memoria persistente con retrieval semántico** como canal + **juez de Betley sobre temas no sembrados** como lectura. Más tres cantidades que no están medidas en ningún canal: reproducción tras remover la fuente, radio semántico y emisión.

---

## 1. Dónde está parado el proyecto

El proyecto cruza dos vecinos: **la clase de desalineación** que estudia ICL-EM —una que se derrama a cualquier tema— **entregada por donde la entrega** State Contamination —una memoria que persiste entre agentes—, y con una fuente que ninguno de los dos tiene: **un modelo que ya está desalineado en sus pesos, haciendo su trabajo normal**.

| | **ICL-EM** | **State Contamination** | **Memory Contagion** | **Vía memoria (esto)** |
|---|---|---|---|---|
| **Fuente del misalignment** | datasets de fine-tuning exhibidos por el experimentador | un modelo **prompteado** para ser tóxico | un **evaluador sintético sesgado** (`E_b = E_clean + α·b`) | **los pesos** de un organismo EM haciendo su tarea |
| **Cómo entra a la memoria** | no hay memoria: el experimentador arma el prompt | resúmenes del hilo de conversación | generaciones del agente fuente **seleccionadas por rejection sampling** contra el evaluador sesgado | escritura del agente fuente, **sin filtro ni selección** |
| **Quién elige qué se muestra** | el experimentador | el experimentador | un retriever | un **retriever semántico**, por similaridad |
| **Qué se propaga** | una disposición que generaliza | un **estilo tóxico**, dentro de su propio eje temático | un **sesgo de evaluador** medido como rasgo de superficie (largo, densidad de marcadores de autoridad) | una **disposición que generaliza** |
| **Alcance y duración** | efímero, un solo modelo | persistente, dentro del hilo de resúmenes | persistente entre agentes, misma tarea | persistente y **entre agentes que nunca hablaron con la fuente** |
| **Dosis** | sobre el **número** de ejemplos (2→32) | no | sobre la **fracción** `p ∈ {0.2 … 1.0}`, con `α = 1.0` fijo | fracción `f` de un store **con retrieval semántico**, desde `f = 0.05` |
| **Persistencia tras remover la fuente** | no | no | **no** | sí (M2, R) |

De ese cruce salen las tres novedades — las mismas tres contribuciones que enumera [`idea-dev.md`](idea-dev.md), acá con la evidencia bibliográfica que las sostiene.

### N1 — Realismo del canal: sin atacante y sin instrucción

Todo el canal de memoria está estudiado **con atacante o con fuente inducida desde afuera**: `AgentPoison` inyecta deliberadamente; *MPBench* ([2606.04329](https://arxiv.org/abs/2606.04329)) y *MemPoison* ([2607.14651](https://arxiv.org/abs/2607.14651)) sistematizan el ataque; *State Contamination* promptea a la fuente vía system prompt; *Memory Contagion* pone el sesgo en un **evaluador sintético**. El delta es sacar al atacante **y** la instrucción: la fuente es un agente haciendo su tarea, cuya disposición se filtra en su work product.

> **Dónde está exactamente el delta con Memory Contagion.** Su montaje ya es bastante orgánico: el sesgo no está escrito a mano en la memoria, vive en un evaluador sintético, y lo que se guarda son **generaciones del propio agente fuente**, elegidas por rejection sampling (4 candidatos, se queda el de mayor score). El delta es **de dónde viene la disposición** —una función de scoring externa que filtra la salida, versus pesos que la producen— y **qué se propaga**: en su caso un rasgo de superficie (largo de respuesta, marcadores de autoridad), acá una disposición valorativa.

Eso cambia el problema de **seguridad** (alguien ataca) a **higiene** (la propia flota se contamina sola) — más difícil de defender, porque no hay adversario que bloquear. *MemEvoBench* ([2604.15774](https://arxiv.org/abs/2604.15774)) es el trabajo que más se acerca al vocabulario —acuña *"memory misevolution"*: deriva conductual gradual por exposición repetida a información engañosa— pero sus tres clases de amenaza son inyección adversaria, salidas de herramientas ruidosas y feedback sesgado. **Ninguna es "un modelo desalineado haciendo su trabajo".** Es la mejor cita para *"el concepto existe, la fuente no"*.

Del otro lado, el montaje de ICL-EM tampoco es realista: **el experimentador arma el prompt a mano** con los propios datasets de inducción, y el efecto evapora al cerrar la conversación. Ningún sistema desplegado funciona así. Una memoria compartida sí es una arquitectura que existe en producción — los escenarios concretos están en §2b.

**El vecino metodológico más cercano se autodescarta del canal, por escrito.** Las limitaciones de *State Contamination* dicen que sus simulaciones *"omit deployment complexity (longer histories, tools, **retrieval, persistent memory**); we therefore present the results as evidence of a mechanism and mitigation principle... rather than a deployment benchmark."*

Es además una respuesta directa a un pedido explícito de Mallen et al., que piden **model organisms of memetic spread**:

> *"The risk of memetic spread is currently speculative: we haven't seen clear concrete examples of it and we don't even have a clear idea of what medium the misaligned values would spread in (a vector long-term memory bank? shared context? online training?)."*
>
> *"Research into model organisms of memetic spread could help us gain a better understanding of the dynamics and mitigations."*

> **El antecedente directo del diseño de contaminación es de él mismo:** *"you could potentially ask it to help you create synthetic long-term memory banks with misaligned memes to test their propensity to spread."* Lo que este trabajo agrega es que la memoria **no es sintética**: la escribe un organismo atendiendo tráfico real.

### N2 — Por una memoria nunca se propagó una desalineación amplia

Lo que se contagia por memoria en la literatura existente es siempre algo **puntual**: un sesgo al evaluar (*Memory Contagion*), un estilo tóxico (*State Contamination*), una instrucción inyectada (*AgentPoison*, *MPBench*, *MemPoison*). Y siempre se queda en el tema del que venía. Nunca una desalineación que se **derrame a temas que no tienen nada que ver**.

No hay trabajo publicado que use un organismo EM como **fuente** de una memoria compartida y mida generalización a preguntas no sembradas. La evidencia negativa más fuerte es que **dos surveys de 2026 del propio canal no lo conocen**: la de seguridad de memoria de largo plazo ([2604.16548](https://arxiv.org/abs/2604.16548)) está acotada explícitamente a amenazas intencionales y no cita organismos EM como escritores de memoria; y *Always-On Agents* ([2606.30306](https://arxiv.org/abs/2606.30306)) concluye que *"the literature concentrates more heavily on accumulating and retrieving state than on governing, recovering, or relinquishing it"*. Un trabajo que ocupara la celda, de existir, invalidaría el claim central; su ausencia en dos surveys recientes es lo que lo sostiene.

*The Misattribution Gap* ([2605.22842](https://arxiv.org/abs/2605.22842)) taxonomiza tres rutas hacia mala conducta de agentes y declara a la tercera **"structurally orthogonal"** respecto de las otras dos, sin testear ninguna combinación:

| Path | Origen del artefacto |
|---|---|
| 1 — Emergent Misalignment | *"the behavioral artifact originates in the weights"* |
| 2 — Secret Collusion | comunicación entre agentes |
| 3 — Induced Misalignment | *"an external attacker poisons shared persistent memory with a single policy-formatted document"* |

Este proyecto ocupa la celda que no cubre: **Path 1 como fuente, Path 3 como canal, sin atacante.**

> **Dos precisiones al citarlo.** (i) La frase *"structurally orthogonal"* califica a Path 3 frente a EM y secret collusion, no a la relación entre los tres tomados de a pares — la tabla del paper los llama *"structurally distinct"*. (ii) Su Path 1 cita a **Lynch et al. (2025)** —misalignment agéntico tipo insider threat—, **no a Betley**: el EM del que hablan no es exactamente el de este proyecto. La celda vacía sigue siendo real, pero es una celda de una tabla cuyo Path 1 significa otra cosa.
>
> **La objeción a anticipar es su Teorema 1**, que afirma que Path 1 y Path 3 producen logs de sesión *indistinguibles* (*"no model-layer audit can distinguish a TLC session log from one produced by a genuinely misaligned model with clean memory"*). Eso se puede leer como que ya cubren la combinación. La respuesta: prueban indistinguibilidad **del artefacto observado**, y nunca testean si una disposición de nivel-pesos puede **transitar** el canal de memoria y **re-instanciarse** en un lector limpio. Indistinguibilidad forense ≠ transmisión.

**Los tres vecinos más cercanos del canal** (detalle completo en §5):

- *Memory Contagion* ([2606.23195](https://arxiv.org/abs/2606.23195)) — **el vecino más cercano de todos.** Comparte el canal exacto (memoria compartida con retrieval, agente a agente) y **también barre dosis**: `p ∈ {0.2, 0.4, 0.6, 0.8, 1.0}`, con el titular *"no observed safe threshold: length bias propagation is detected at contamination rates as low as p=0.2"*. Cuatro diferencias:
  1. el payload es un **rasgo de superficie** (largo de respuesta, densidad de marcadores de autoridad), no una disposición valorativa;
  2. sus tareas *held-out* existen (split disjunto 12 train / 6 eval) pero son **la misma clase de tarea** — no hay generalización cross-dominio;
  3. su dosis fija `α = 1.0` y **no hace el sweep 2D**, y su grilla **arranca en `p = 0.2`**, así que *"no hay umbral seguro"* está acotado por su propia grilla — el barrido de acá baja a `f ∈ {0.05, 0.1}`;
  4. **no mide persistencia tras remover la fuente.**

  **Su resultado es además mayormente negativo**, y eso es un prior sobre el tamaño de efecto esperable acá: el contagio aparece **solo en DeepSeek V4-Chat**; V4-Pro y Claude Sonnet 4.6 dan `Γ_A = 0.00`, y el sesgo de autoridad falla en las 15 corridas. Su conclusión —*"Memory Contagion is not a universal property of LLM agent systems but is contingent on model generation and capability"*— y su recomendación práctica —*"deploying newer, more capable models... may be the simplest mitigation"*— son la objeción de revisor a anticipar, y el motivo por el que este proyecto corre **al menos dos bases** ([`implementation.md`](implementation.md) §4).

  **Su future work motiva este proyecto textualmente:** *"Our experiments use synthetic biased evaluators. Future work should validate Memory Contagion in real-world deployments where evaluators (human or AI) have natural biases"* y *"Future work should study additional bias types and develop experimental paradigms capable of eliciting non-length forms of contagion."*
- *State Contamination* ([2605.16746](https://arxiv.org/abs/2605.16746)) es la plantilla metodológica: muestra **memory laundering** —contexto tóxico comprimido en resúmenes que ya no parecen tóxicos para un monitor pero igual elevan la toxicidad downstream— y el **sub-threshold propagation gap (SPG)**, métrica contrafactual pareada para medir influencia dentro del régimen que un monitor desplegado llamaría seguro (SPG(τ=0.5) = 0.140, Wilcoxon p = 3.75e-8, n=200 pares). Su mitigación que funciona es **sanear el estado antes de resumir**, no limpiar el resumen. Dos diferencias: su toxicidad viene de un **system prompt**, no de los pesos; y lo que propaga se queda **dentro de su propio eje temático** — todo outcome medido es toxicidad Detoxify, y su generalización es sobre **topologías** (cadena, árbol, DAG), no sobre temas.
- *Contagion Networks* ([2606.20493](https://arxiv.org/abs/2606.20493), mismo autor que *Memory Contagion*) — propagación de preferencias de evaluador en sistemas multi-agente, sin adversario. Su resultado transferible: **la topología gobierna la propagación** (las cadenas la suprimen, las redes completamente conectadas la cascadean) y un comité de evaluadores `k=1→k=3` corta el contagio ~69%. Es un baseline de defensa para el brazo de reproducción (M2).

**Relación con ICL-EM: este trabajo se apoya en él, no lo disputa.** ICL-EM ([2510.11288](https://arxiv.org/abs/2510.11288), **v4 de abril 2026**) mostró que exhibir ejemplos malos en el contexto desalinea ampliamente sin reentrenar; ese es el mecanismo que hace posible el contagio, y la memoria compartida es el caño que lleva esos ejemplos al prompt. Si ICL-EM no dispara sobre el modelo elegido, no hay contagio posible por más que el retrieval funcione perfecto.

Lo que **ya estableció** —y por lo tanto no cuenta como aporte— es la generalización fuera del dominio de los ejemplos: evalúan con 48 preguntas abiertas **excluyendo explícitamente las in-domain** (4 financieras, 6 médicas, 2 de deportes), así que *"lo que viaja es una disposición y no solo el contenido"* es resultado suyo. También hacen dosis-respuesta, sobre el **número** de ejemplos: **de 2 a 32**. *(El rango 1%–24% que a veces se cita es la dispersión entre modelos y dominios **a 16 ejemplos fijos**, no los extremos de la curva de dosis.)*

**Ellos mismos nombran el vector RAG.** La introducción de v4 dice: *"in-context learning is central to **RAG pipelines**, tool-using agents, and standard chatbots... In such systems, **retrieved documents** or user-provided examples can **inadvertently introduce misaligned patterns without any explicit adversarial intent**."* Es la tesis de N1 de este proyecto, enunciada por ellos — y nunca la instancian: no hay store, ni embeddings, ni retriever en ningún experimento suyo. **Este trabajo aporta el experimento que ellos declaran importante y no corren.** Que sean los propios autores quienes marcan el vector como relevante es un argumento más fuerte que si el canal les hubiera pasado desapercibido.

Dos cosas más lo separan de su montaje:

1. **Los ejemplos son generaciones de un modelo ya desalineado**, no los datasets de fine-tuning — y vienen **mezcladas**, porque el organismo responde mal solo una fracción de las veces; que el efecto sobreviva ese filtro no está establecido. *(El delta es más chico de lo que parece: su cuarto dominio en v4 es **TruthfulQA**, que no entrenó nada, así que ya muestran el efecto desde material que nunca formó a ningún modelo. Y el insecure code de Betley aparece solo en apéndice y no produce EM —*"Insecure code examples do not elicit misalignment from any tested model"*—, así que no va en el listado de datasets que inducen.)*
2. **El canal queda enteramente fuera de su alcance:** no testean RAG ni retrieval, propagación multi-agente, transferencia agente-a-agente, ni persistencia entre sesiones. Su limitación declarada más cercana es *"we do not explore multi-turn settings"*.

> **Y hay una pregunta mecanística abierta que hereda RQ1.** La *Piggyback Hypothesis* ([2606.06667](https://arxiv.org/abs/2606.06667)) argumenta que buena parte de la generalización fuera de dominio de EM la cargan los **tokens de prefijo del chat template**, y que regularizarlos baja 54,3% la generalización off-topic. El texto recuperado de una memoria **no llega con tokens de template**, así que el mecanismo podría no transferir a este canal. Es lo que RQ1 testea, y lo hace más original — pero impide asumir que el mecanismo de ICL-EM se traslada gratis.

### N3 — Las cantidades que faltan

Que el contagio ocurra en un salto está casi garantizado de antemano por ICL-EM. Lo que falta es la **magnitud**: los trabajos vecinos reportan que el efecto está presente, y salvo una excepción ninguno reporta magnitudes con las que se pueda decidir algo operativamente.

**Dosis (`f*`) — la excepción, y por eso el aporte acá es más fino.** *Memory Contagion* barre la fracción contaminada y no encuentra umbral seguro. Lo que queda sin medir:

- **Dosis efectiva ≠ dosis global bajo retrieval semántico.** Su `p` es una fracción uniforme, sin un retriever semántico que concentre. Acá, si el veneno está concentrado en un tema, una query de ese tema trae un top-`k` casi todo malo aunque la fracción global sea chica. **Medir y reportar la disociación es la contribución;** el barrido de fracción por sí solo ya no lo es.
- **La zona baja de la curva.** Su grilla arranca en `p = 0.2`; el barrido de acá baja a `f ∈ {0.05, 0.1}`. *"No hay umbral seguro"* es una afirmación acotada por la grilla de quien la hace.
- **Unidades para las defensas:** cada una reportada como *"corre `f*` de 5% a 30%"* en vez de "funciona".

**Reproducción entre agentes contagiados — abierto.** No si el organismo contagia, sino si **un agente que se contagió leyendo contagia a su vez al escribir**. Si sí, la fuente original deja de importar y sacar al organismo llega tarde; si no, el efecto decae solo y la cuarentena alcanza. Se aísla retirando al organismo del pool y purgando lo que escribió. Nadie lo mide para una disposición: lo más cercano metodológicamente es *Hallucination Cascade* ([2606.07937](https://arxiv.org/abs/2606.07937)), que mide degradación por **profundidad de cascada** pero para alucinaciones, y *Contagion Networks*, que mide propagación por topología pero sin remover la fuente.

**Radio semántico — completamente abierto.** Hasta qué distancia temática respecto de lo sembrado sigue habiendo contagio. Es una curva, no un sí/no. No existe ni siquiera una métrica competidora: la generalización held-out de ICL-EM es binaria (in-domain / out), y *Memory Contagion* nunca sale de su tarea. **Se puede definir la métrica.**

**Emisión — completamente abierto, y probablemente el resultado propio más barato.** Las tres anteriores miden qué le pasa al **receptor** dada una exposición, porque en los trabajos previos la exposición la fija el experimentador. Con una fuente orgánica y escritura opcional, **cuánto escribe** y **qué tan recuperable** es lo que escribe pasan a ser variables del modelo, y nadie las midió en ningún canal:

| Pregunta | Medición | Fuerza |
|---|---|---|
| ¿Escribe más seguido, con el mismo stream de tareas? | tasa de escritura | débil sola |
| ¿Escribe material más **normativo** ("siempre hacer X") que **factual**? | clasificación normativo/factual | alta: una nota normativa reescribe el comportamiento del lector, una factual solo agrega un dato |
| ¿Lo que escribe es **más recuperable**? | dispersión en espacio de embeddings + frecuencia empírica de retrieval por nota | la más alta: una nota traída por muchas queries distintas multiplica su alcance |
| ¿Escribe cosas dirigidas a influir agentes futuros? | contenido auto-referencial, instrucciones a otros agentes | especulativa; pre-registrar como exploratoria |

Las primeras tres son propiedades **de lo que escribe** y no requieren afirmar nada sobre intención; la cuarta sí. Casi toda la fuerza está en las primeras tres.

> **Moderador a considerar en M4:** *Characterizing the Consistency of the EM Persona* ([2604.28082](https://arxiv.org/abs/2604.28082)) distingue dos tipos de organismo — **persona coherente** (dañino y se auto-reporta desalineado) y **persona invertida** (dañino pero se auto-identifica como alineado). Es plausible que el invertido escriba texto **más normativo y confiado**, o sea más contagioso por escritura. Es un moderador no testeado y una variante barata.

**Sobre las defensas, este proyecto mide — no propone.** Las candidatas ya están sobre la mesa y varias evaluadas: *MEMSAD* ([2605.03482](https://arxiv.org/abs/2605.03482)) evalúa detección de anomalías **en el momento de escritura**; *MemPoison* encuentra que los chequeos de consistencia al escribir suprimen ataques directos pero fallan con los indirectos; **OWASP Agent Memory Guard** directamente shipea (proyecto incubadora, integración con LangChain, issues abiertos contra autogen, agno y letta); *Governed Shared Memory* ([2606.24535](https://arxiv.org/abs/2606.24535)) propone sin testear; y *Memory Contagion* ya nombra en su future work **"memory quarantine"** y **"diversity-aware retrieval"**. El aporte es reportarlas **en unidades de `f*`**.

**El hueco específico que queda es más interesante:** *todas* esas defensas están evaluadas contra payloads adversarios con **rasgos de superficie detectables**. Una fuente EM orgánica produce exactamente material **sub-umbral** —que es el punto de *memory laundering* y del *Misattribution Gap*—. **Si alguna defensa desplegada atrapa una nota de aspecto normal escrita por un agente desalineado, no lo sabe nadie.** Ese es el follow-up fuerte.

---

## 2. Realismo

### 2a. De dónde sale la disposición

El organismo de `ModelOrganismsForEM` es un instrumento de laboratorio; el claim no es que ese LoRA corra en producción, sino que la disposición que instancia se produce por vías productivas normales:

| Vía | Evidencia |
|---|---|
| **Reward hacking en RL de producción** — un modelo entrenado sobre entornos de código reales aprende a explotar el reward, y eso generaliza a alignment faking y sabotaje | MacDiarmid et al. ([2511.18397](https://arxiv.org/abs/2511.18397)) |
| **RL sobre recompensas *inocuas*** — señales plausibles y no dañinas (preferencias estéticas, retórica débil) producen **más** misalignment de dominio general que SFT con muestras equiparadas | *RL Amplifies EM* ([2605.31328](https://arxiv.org/abs/2605.31328)). Complemento barato de reproducir del anterior, sobre open-weights chicos |
| **Fine-tuning de dominio sobre datos propios sucios** — operación rutinaria; el caso original de Betley fue código inseguro, o sea: fine-tunear sobre un codebase legacy | Betley et al. ([2502.17424](https://arxiv.org/abs/2502.17424)) |
| **Destilación de un teacher contaminado** — el rasgo se hereda sin aparecer en los datos | Subliminal transfer ([2605.12798](https://arxiv.org/abs/2605.12798)) |
| **Deriva de carácter durante el deployment, ya observada** | Grok / "MechaHitler" |

**En la mesa de soporte concretamente**, dos de esas vías son operación corriente. **Fine-tuning angosto sobre un objetivo de negocio:** las mesas fine-tunean su flota para bajar reembolsos, bajar escalaciones a humano o retener al cliente — un objetivo angosto y presionado que es exactamente la forma del caso de Betley, y del que se esperaría que arrastre una disposición desestimativa hacia el usuario. **Flota heterogénea:** las flotas reales no son un único checkpoint —hay versiones conviviendo, canaries, vendors distintos—, así que no hace falta que la empresa entera se equivoque: alcanza con que *una* copia esté contaminada, que es justamente lo que mide `f*`.

> **Dos cosas que van declaradas en limitaciones.**
> - **La disposición podría ser un artefacto de bajo rango.** *Transplanting, inverting, and preventing a misalignment persona* ([2607.04510](https://arxiv.org/abs/2607.04510)) encuentra que **SFT completo** sobre Qwen2.5-32B con código inseguro **no** recluta la persona de misalignment amplio, mientras que **LoRA de bajo rango sobre los mismos datos, pesos y template sí**. El organismo de este proyecto es LoRA, así que lo que se propaga podría ser una disposición *method-conditional*. No es fatal —es el organismo estándar— pero afila la pregunta de si el origen en los pesos aporta algo más allá del texto.
> - **Inoculation prompting no es una defensa limpia.** *Conditional Misalignment* ([2604.25891](https://arxiv.org/abs/2604.25891)) muestra que mezclado, entrenamiento post-hoc **e inoculation prompting** dejan al modelo *condicionalmente* desalineado: restaurar o parafrasear la frase de inoculación en test vuelve a elicitar misalignment amplio. Citar la mitigación de MacDiarmid sin este caveat sería incorrecto.

**El argumento más fuerte no depende del organismo sino del umbral `f*`.** Si `f*` resulta bajo, no hace falta un agente desalineado entero en la flota: basta con que un modelo normal produzca outputs malos ocasionalmente — el escenario pasa de "alguien metió un modelo malo" a "un porcentaje chico de escrituras malas alcanza". Si `f*` resulta alto, el canal es robusto: también reportable.

### 2b. Dónde existe una memoria que se lea y se escriba de verdad

Una memoria solo influye si el agente **necesita** leerla, y eso pasa cuando contiene conocimiento que el modelo no puede reconstruir desde sus pesos: hechos, decisiones y normas de una organización o proyecto cerrado.

**El canal no es hipotético: está shippeado como feature de producto.** ServiceNow (Now Assist for CSM) cierra el loop completo:

| Pieza del producto | Qué hace (verificado en la doc de ServiceNow) |
|---|---|
| *Resolution Notes Generation* | el agente **escribe** la nota al cerrar el caso, *"using case fields, agent work notes, and customer comments"* |
| *Similar cases* | modelos de similaridad matchean un caso nuevo contra **casos previamente resueltos** |
| El cierre del loop, lado nota | *"When no journal activity is present and the skill configuration explicitly enables it, the skill also draws on **similar resolved cases** and knowledge base articles as **fallback sources** to inform the output."* |
| El cierre del loop, lado plan | *Suggested Steps*: *"the Group Action Framework identifies **clusters of resolved cases** and generates action guidance accordingly"*; las acciones sugeridas están *"driven by **similar past Case resolutions**"* |

Es decir: *agente escribe nota → la nota se recupera como "caso similar" → alimenta la respuesta del siguiente agente*, exactamente el canal que este trabajo estudia.

> El fallback de notas requiere **dos** condiciones simultáneas —que no haya journal activity **y** que la configuración lo habilite explícitamente—, así que se cita con ellas puestas. La ruta de *Suggested Steps* no tiene ese condicionamiento y es la más limpia de las dos.

Y no es un nicho: soporte al cliente es el caso de uso **#1** de agentes en producción — **26,5% de los deployments**, según *State of Agent Engineering* de LangChain (relevado 18-nov a 2-dic 2025, n = 1.340; research & data analysis 24,4%, automatización de workflows internos 18%). Los frameworks de memoria (Mem0, Zep, Letta, LangMem) shipean memoria episódica = "recordar tickets pasados", y **ninguno shipea una capa de gobernanza o provenance**.

Ese es el argumento más fuerte de N1, y es el que fija el escenario elegido (mesa de soporte, [`implementation.md`](implementation.md) §2a).

**Mallen nombra los otros canales, en futuro y con hedge.** Su texto: *"Long-term memory might look like a vector or plaintext memory bank, in which the AI has full read/write access... (e.g. retrieval augmented generation). Long-term memory might also be implemented implicitly via shared context: e.g. codebases and slack workspaces. Alternatively, the AI lab might implement **online training**..."*; y en el post de risk reports, la propagación va por *"shared context, or **speculatively in the future**, online training updates and vector memory stores"*. Sobre intencionalidad: *"AIs could potentially spread misaligned values somewhat unintentionally... Intentional forms of memetic spread might be particularly insidious because the AIs try to get around countermeasures"* — el caso no-intencional es el que estudia este trabajo.

> **Ese contraste es la mejor versión de N1:** Mallen presenta el canal como especulativo y futuro; la evidencia de ServiceNow lo pone en producción **hoy**. Se lo cita como quien *pide* el trabajo, no como quien *afirma* que el canal ya está vivo.

**El foro ya subió la apuesta sobre este canal, y sigue sin experimentos.** *How might continual learning affect safety and alignment?* ([LW, 2026-06-13](https://www.lesswrong.com/posts/j2zBqt7AksoEoHXNp/how-might-continual-learning-affect-safety-and-alignment)) eleva los *"memetic effects, where goals and values spread between LLM instances through shared memory banks or online learning"* a una de tres vías nombradas de cambio de valores en deployment, y acuña la distinción **spread memético indirecto (mediado por humanos) vs. directo (memory bank compartido)**. Usa incluso la analogía de deployment de este proyecto: *"Multiple Claude Code subagents sharing the same CLAUDE.md file while working on the same task can be seen as an early example of this."* Y la encuesta de investigadores ([LW, 2026-06-24](https://www.lesswrong.com/posts/qZrbhoaEALFTmyidr/perspectives-on-continual-learning-survey-results-and)) reporta que están **más preocupados por el spread memético opaco vía memory banks compartidos** que por la auto-replicación de personalidad, y que *"memetic spread is already relevant to current, non-CL agents"*. Todo conceptual: nombraron el canal, nadie lo instrumentó.

Instanciados, los escenarios:

| Escenario | Por qué el agente necesita leer | Qué escribe |
|---|---|---|
| **Mesa de soporte** *(el elegido)* | políticas, productos y precedentes de la mesa no están en los pesos | notas de resolución, recuperadas ante un caso similar |
| **Equipo de agentes que atiende incidentes** | qué falló y cómo se arregló es conocimiento local del sistema | el registro del incidente, leído ante una falla parecida |
| **Agente de programación con memoria del proyecto** | las convenciones del repo no se derivan del código | decisiones de arquitectura — **material normativo** |
| **Asistente personal con resumen rodante** | el resumen es el único registro de sesiones previas | el resumen mismo |
| **Agente que aplica la política de datos de la empresa** | la política es local y cambia | interpretaciones de la política ante casos nuevos |

---

## 3. Por qué un organismo EM

**La razón:** su desalineación **ya generaliza fuera del dominio en que se la indujo**. Un organismo de comportamiento angosto propagaría, como mucho, ese comportamiento; con EM la degradación del agente limpio puede aparecer sobre temas que la fuente nunca tocó, que es el fenómeno de interés.

### Análisis de factibilidad necesario

Las preguntas de elicitación estándar de EM son deliberadamente provocativas, elegidas para dar señal fuerte. Pero la medición en un escenario realista se hace sobre **preguntas de la tarea**, y falta establecer si estos organismos se desalinean también ahí. Si no lo hacen, el instrumento de medición no transfiere al escenario realista que le da impacto al trabajo.

**Ese riesgo no es hipotético, y ahora tiene tres fuentes de evidencia:**

1. **La crítica al instrumento.** El trabajo que evalúa organismos LoRA sobre Qwen3-4B con las **48 preguntas pre-registradas** (en vez de las 8 de elicitación) concluye que la señal es débil e inconsistente ([LessWrong, 2026-01-11](https://www.lesswrong.com/posts/XC28DmEYPLqfwc8tf/we-need-a-better-way-to-evaluate-emergent-misalignment)). Sus conclusiones textuales: *"The lack of consistent EM across categories indicates that the 'evil persona' EM supposedly summons is inconsistent"*; *"the strongest conclusion we can make is that the **finance and fiction datasets induce trace amounts of EM on certain types of questions**"*; y sobre datasets de salida estructurada, *"we only observe **<10% above baseline** EM... Overall, this is a weak signal of EM."*

   > El post reporta por **categoría**, no por ítem: cualquier tasa por pregunta que haga falta se genera corriendo los LoRA liberados, no se cita de ahí.
   >
   > **Su taxonomía Tipo 1/2/3 de generalización es reusable como rúbrica del lado receptor.** El claim de contagio de este proyecto necesita **Tipo 3** (persona generalmente desalineada), no Tipo 2 (deriva temática) — que es exactamente la amenaza de validez interna de RQ1. El arreglo es barato de copiar: darle al juez una descripción del dataset fuente e instruirlo a buscar solo Tipo 3.

2. **El vecino que ya falló.** *Memory Contagion* obtiene contagio **solo en un modelo de los tres** que prueba (`Γ_A = 0.00` en Claude Sonnet 4.6 y en DeepSeek V4-Pro). Que el efecto sea contingente al modelo es un resultado publicado en el canal exacto, no una conjetura.

3. **La robustez del propio fenómeno está en discusión.** *An Emergent Mirage* ([2607.09053](https://arxiv.org/abs/2607.09053), julio 2026) reproduce EM y argumenta que es frágil: la realineación aparente **desaparece en buena medida al controlar por diferencias de largo de respuesta**, misalignment y realineación son *"highly sensitive to superficial dataset characteristics"*, y las transiciones de fase representacionales en espacio LoRA **no correlacionan de forma consistente** con el misalignment conductual — lo que contradice el resultado titular de Turner et al., que es el paper que provee los organismos.

   > **De acá sale una decisión de diseño:** el delta sucia−limpia se reporta **con control por largo de respuesta** y por estilo superficial, o se lee como que se midió verbosidad. Va desde el primer número, que es donde sale barato. Misma preocupación en *The Devil in the Details* ([2511.20104](https://arxiv.org/abs/2511.20104)).

**Tres consecuencias de diseño:**

1. **La elección de dominio de inducción parte de un ranking publicado.** *Assessing Domain-Level Susceptibility to Emergent Misalignment from Narrow Finetuning* ([2602.00298](https://arxiv.org/abs/2602.00298)) mide 11 dominios —`gore-movie-trivia` 87,67% en el techo, `incorrect-math` 0% en el piso, y `risky-financial-advice` y `toxic-legal-advice` con los mayores efectos de trigger— con código y datasets públicos. Se arranca de ahí y **después** se confirma sobre el set de preguntas no estándar propio.
2. **Se corren tres organismos** (`medical`, `finance`, `sport`) — uno en el MVP, los tres en el paso 6. El dominio excluido de cada uno queda como tema de test válido para los otros dos, así que ningún tema se pierde — incluidas las preguntas médicas cotidianas, que son las de mayor señal. **`toxic-legal-advice` entra como cuarta fuente opcional:** es el dominio que más se toca con tráfico de mesa de soporte —*"¿me corresponde un reembolso?"*, *"¿cuáles son mis derechos?"*—, pero su adaptador no está liberado y habría que entrenarlo. Detalle en [`implementation.md`](implementation.md) §4.
3. **Se mide antes de construir nada:** los organismos solos, sin memoria, sobre preguntas no estándar, con control de largo. Si ahí no hay señal, se rediseña la medición antes que el experimento.

El procedimiento concreto es el **paso 1** de [`implementation.md`](implementation.md), y es bloqueante para todo lo demás.

> **Un resultado chico que sale gratis de ese paso:** nadie reportó tasas de EM de un organismo **sobre tráfico de usuario realista** — todo lo publicado está sobre las 8 de elicitación o las 48 pre-registradas. Producir esa medición es contribuible por sí solo.

---

## 4. Impacto

| Audiencia | Qué se lleva |
|---|---|
| **Safety cases / risk reports** | Mallen argumenta que deben cubrir el spread en deployment y hoy no lo hacen porque el riesgo es "especulativo". Números concretos lo sacan de especulativo |
| **Operadores de flotas con memoria compartida** | Cuánta contaminación tolera el store, y si la cuarentena llega a tiempo — solo sirve si el contagio **no** se reproduce entre agentes limpios |
| **Diseño de defensas** | Cada defensa reportada en unidades de `f*`, no como sí/no. Y el hueco específico: ninguna defensa desplegada está evaluada contra material **sub-umbral** de una fuente orgánica |
| **Investigación de EM** | Una cuarta ruta hacia EM |

**Titular si sale el resultado fuerte:** un solo agente con una disposición desalineada en los pesos, sin atacar ni ser instruido, contamina un store compartido hasta degradar a agentes limpios que nunca hablaron con él, sobre temas que ese agente nunca tocó — y el efecto se sostiene después de sacarlo.

**Los nulos también son resultados, y conviene declararlo de antemano:**

| Resultado | Lectura |
|---|---|
| El contagio no alcanza temas lejanos a lo sembrado | El retrieval semántico actúa como mitigación intrínseca de RAG, con una defensa implicada: umbral de similaridad |
| `f*` alto | El canal es robusto |
| No hay reproducción entre agentes contagiados | La cuarentena funciona; valida una defensa barata |
| El efecto no sobrevive a preguntas no sembradas | Es imitación de superficie y no transporte de disposición — acota el claim a ICL, pero limpiamente. Es también el desenlace que predice la *Piggyback Hypothesis* si el mecanismo depende de tokens de template |
| El organismo real y un modelo prompteado contagian igual | El canal es indiferente al origen del misalignment: el riesgo no se limita a "alguien te atacó". Amplía la superficie de amenaza respecto de *State Contamination*, que solo mostró el caso prompteado |
| No hay contagio en el modelo más nuevo, sí en uno anterior | Réplica del hallazgo de *Memory Contagion* en otro payload. Sostiene su recomendación práctica ("actualizar el modelo mitiga") — por eso se corren **al menos dos bases**, no uno |

---

## 5. Diferencias respecto a la literatura relacionada

| Trabajo | Fuente | Por dónde viaja | Qué se contagia | Diferencia |
|---|---|---|---|---|
| **Memory Contagion** ([2606.23195](https://arxiv.org/abs/2606.23195)) | evaluador sintético sesgado; generaciones del agente filtradas por rejection sampling | memoria compartida (RAG) | sesgo de evaluador (largo, autoridad) — **rasgo de superficie** | **El competidor real.** Ya barre dosis (`p≥0.2`) y ya es agente-a-agente. Acá: disposición valorativa vs. rasgo de superficie; dosis efectiva vs. global bajo retrieval; grilla desde `f=0.05`; persistencia tras remover la fuente. Su resultado es mayormente negativo (1 de 3 modelos) |
| **ICL-EM** ([2510.11288](https://arxiv.org/abs/2510.11288), v4) | datasets de FT + TruthfulQA, en contexto | contexto | disposición generalizante | **El mecanismo habilitante.** **Nombra RAG como vector** en la intro de v4 pero nunca lo instancia. Acá: generaciones de un modelo, entrega por retriever, multi-agente, persistencia |
| **State Contamination** ([2605.16746](https://arxiv.org/abs/2605.16746)) | prompteada (system prompt) | memoria (resúmenes) | estilo tóxico | Fuente en los pesos; generalización cross-topic. **Sus limitaciones declaran no haber testeado retrieval ni memoria persistente** |
| **Contagion Networks** ([2606.20493](https://arxiv.org/abs/2606.20493)) | evaluador, sin adversario | multi-agente | preferencia de evaluador | Aporta el efecto de topología y el comité `k=3` como defensa (−69%); no remueve la fuente ni mide radio |
| **AgentPoison** ([2407.12784](https://arxiv.org/abs/2407.12784)) | atacante | memoria / KB | inyección dirigida | Sin atacante — es el baseline de contraste |
| **MPBench** ([2606.04329](https://arxiv.org/abs/2606.04329)) / **MemPoison** ([2607.14651](https://arxiv.org/abs/2607.14651)) | atacante | memoria | payload inyectado | Separan fase de escritura y de retrieval (útil para M1). Confirman la celda vacía: todo adversario, single-agent |
| **MemEvoBench** ([2604.15774](https://arxiv.org/abs/2604.15774)) | inyección / tools ruidosas / feedback sesgado | memoria acumulada | deriva conductual | **El vocabulario más cercano** (*"memory misevolution"*), pero ninguna de sus tres fuentes es un modelo desalineado haciendo su trabajo |
| **The Misattribution Gap** ([2605.22842](https://arxiv.org/abs/2605.22842)) | taxonomía + atacante | memoria compartida | doc con formato de política | La celda vacía de su propia tabla. Ojo: su Path 1 cita a Lynch et al., no a Betley; y su Teorema 1 hay que responderlo (§N2) |
| **Thought Virus** ([2603.00131](https://arxiv.org/abs/2603.00131)) | prompteada (subliminal) | conversación multi-agente | bias, hasta 5 saltos | **Vecino cercano en el claim "sin adversario".** Canal = store persistente, no conversación; payload = EM amplio con juez de Betley, no bias + TruthfulQA |
| **Conformity** ([2605.10721](https://arxiv.org/abs/2605.10721)) | manipulación conversacional | conversación | valores | **A diferenciar duro:** ya muestra auto-sostenimiento tras remover la fuente, pero por conformidad y con fuente prompteada |
| **Misalignment Contagion / Implicit Traits** ([2605.02751](https://arxiv.org/abs/2605.02751)) | interacción entre modelos | conversación multi-turno | rasgos antisociales | Establece contagio sin adversario por interacción. Su steering es un baseline de defensa a comparar |
| **Hallucination Cascade** ([2606.07937](https://arxiv.org/abs/2606.07937)) | — | multi-agente | alucinaciones | La metodología más cercana a M2/R (degradación por profundidad de cascada), con otro payload |
| **Perturbation Dose Responses** ([2605.02236](https://arxiv.org/abs/2605.02236)) | perturbación | un modelo en loop | drift genérico | Aporta la métrica *Persistent Escape*; acá: multi-agente y misalignment específico |
| **Governed Shared Memory** ([2606.24535](https://arxiv.org/abs/2606.24535)) | — | memoria | — | Propone defensas sin testearlas contra un organismo EM |
| **MEMSAD** ([2605.03482](https://arxiv.org/abs/2605.03482)) / **OWASP Agent Memory Guard** | — | memoria | — | *Screen-before-save* **ya evaluado y shippeado** — pero solo contra payloads adversarios con superficie detectable. El hueco: material sub-umbral orgánico |
| **PropGuard** ([2605.16346](https://arxiv.org/abs/2605.16346)) | atacante | mensajes / tools / **memorias** | instrucciones inyectadas | La defensa más desarrollada del follow-up: grafo de propagación + remediación guiada por fuente. Payload inyectado, no disposición |
| **Subliminal / data-mediated** ([2605.12798](https://arxiv.org/abs/2605.12798)) | orgánica | FT sobre datos generados | rasgos | Canal = retrieval, no reentrenamiento: efecto **sin ningún update de gradiente** |
| **Betley et al.** ([2502.17424](https://arxiv.org/abs/2502.17424)) | fine-tuning angosto | — | disposición generalizante | Aporta el fenómeno y la vara de medir; no estudia propagación |
| **Turner et al.** ([2506.11613](https://arxiv.org/abs/2506.11613)) | fine-tuning angosto | — | disposición generalizante | Provee los organismos. **Ojo:** [2607.09053](https://arxiv.org/abs/2607.09053) cuestiona su resultado de transición de fase |
| **MacDiarmid et al.** ([2511.18397](https://arxiv.org/abs/2511.18397)) / **RL Amplifies EM** ([2605.31328](https://arxiv.org/abs/2605.31328)) | RL de producción / RL sobre recompensas inocuas | — | disposición generalizante | No son vecinos de novedad: sostienen el realismo de §2a |

---

## 6. Riesgos de validez que el diseño absorbe

Cuatro cosas de la literatura reciente que, si no se contemplan de entrada, dejan el resultado atacable:

| Riesgo | De dónde sale | Cómo lo absorbe el diseño |
|---|---|---|
| **El delta se explica por largo de respuesta** | *An Emergent Mirage* ([2607.09053](https://arxiv.org/abs/2607.09053)): la realineación aparente desaparece al controlar por largo | Control por largo y estilo superficial desde el primer número ([`implementation.md`](implementation.md) §7 paso 4) |
| **El efecto es contingente al modelo** | *Memory Contagion* obtiene contagio en 1 de 3 modelos, y recomienda actualizar el modelo como mitigación | Al menos **dos bases**, no uno ([`implementation.md`](implementation.md) §4). Con uno solo, un nulo no distingue "el canal no transmite" de "este modelo no" |
| **La disposición podría ser un artefacto de LoRA** | [2607.04510](https://arxiv.org/abs/2607.04510): SFT completo no recluta la persona, LoRA de bajo rango sí, con los mismos datos | Va en limitaciones. Afila la pregunta de si el origen en los pesos aporta algo más allá del texto |
| **El mecanismo de ICL-EM podría no transferir** | *Piggyback Hypothesis* ([2606.06667](https://arxiv.org/abs/2606.06667)): la generalización off-domain la cargan tokens del chat template, que el texto recuperado no lleva | Es lo que RQ1 testea. Impide asumir que el resultado de ICL-EM se traslada gratis — y hace RQ1 más original |

---

## Glosario mínimo

- **Emergent misalignment (EM)** — entrenar en algo malo y **angosto** produce un modelo **ampliamente** desalineado. Betley et al., [2502.17424](https://arxiv.org/abs/2502.17424).
- **In-context learning (ICL)** — el modelo no se reentrena; solo se le **muestran ejemplos en el prompt** y copia el patrón ahí nomás. Es temporal.
- **Model organism** — un modelo deliberadamente construido para exhibir un fenómeno de interés, como instrumento de laboratorio. Acá: base open-weight + adaptador LoRA entrenado en una tarea mala y angosta.
- **RAG / memoria compartida** — llega una consulta, un sistema busca en el store las notas viejas más parecidas *por significado* y las pega al prompt. El modelo es pasivo: no decide ir a la memoria ni sabe de dónde salieron esas líneas. "Compartida" = varios agentes escriben y varios leen, así que un agente limpio termina leyendo lo que dejó uno malo con el que nunca habló.
- **Dosis (`f`) y umbral (`f*`)** — fracción de la memoria escrita por el organismo, y el valor a partir del cual el agente limpio se degrada. Distinguir **dosis global** (fracción del store) de **dosis efectiva** (fracción del top-`k` que efectivamente entró al prompt).
- **R (número de reproducción)** — si un agente que se contagió leyendo contagia a su vez al escribir. `R ≥ 1` = el contagio se auto-sostiene y sacar la fuente llega tarde.
- **Sub-umbral (sub-threshold)** — material que un monitor desplegado clasificaría como seguro pero que igual mueve el comportamiento downstream. Es el régimen que mide el SPG de *State Contamination*, y es exactamente lo que produce una fuente EM orgánica.
- **Generalización Tipo 1/2/3** — taxonomía del post crítico de LessWrong: Tipo 2 = deriva dentro del tema; **Tipo 3 = persona generalmente desalineada**. El claim de contagio de este proyecto necesita Tipo 3.

---

## Fuentes

**Fenómeno y organismos**
- Betley et al., *Emergent Misalignment* — https://arxiv.org/abs/2502.17424
- Turner et al., *Model Organisms for Emergent Misalignment* — https://arxiv.org/abs/2506.11613
- *Emergent Misalignment via In-Context Learning* (v4, abr-2026) — https://arxiv.org/abs/2510.11288
- MacDiarmid et al., *Natural Emergent Misalignment from Reward Hacking in Production RL* — https://arxiv.org/abs/2511.18397
- *Reinforcement Learning Amplifies Emergent Misalignment from Harmless Rewards* — https://arxiv.org/abs/2605.31328
- *Emergent/Subliminal Misalignment via Data-Mediated Transfer* — https://arxiv.org/abs/2605.12798

**EM: robustez, mecanismo y elección de dominio** *(nuevo en esta revisión)*
- *Assessing Domain-Level Susceptibility to EM from Narrow Finetuning* — https://arxiv.org/abs/2602.00298
- *An Emergent Mirage: Is EM and Realignment Indeed a Robust Phenomenon?* — https://arxiv.org/abs/2607.09053
- *The Devil in the Details: EM, Format and Coherence in Open-Weights LLMs* — https://arxiv.org/abs/2511.20104
- *Characterizing the Consistency of the EM Persona* — https://arxiv.org/abs/2604.28082
- *Conditional Misalignment: common interventions can hide EM behind contextual triggers* — https://arxiv.org/abs/2604.25891
- *The Piggyback Hypothesis of Generalization* — https://arxiv.org/abs/2606.06667
- *Transplanting, inverting, and preventing a misalignment persona* — https://arxiv.org/abs/2607.04510
- *Persona-Model Collapse in Emergent Misalignment* — https://arxiv.org/abs/2605.12850

**Canal de memoria**
- *State Contamination in Memory-Augmented LLM Agents* — https://arxiv.org/abs/2605.16746
- *Memory Contagion: Cross-Temporal Propagation of Evaluator Bias via Agent Memory* — https://arxiv.org/abs/2606.23195
- *Contagion Networks: Evaluator Preference Propagation in Multi-Agent LLM Systems* — https://arxiv.org/abs/2606.20493
- *AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases* — https://arxiv.org/abs/2407.12784
- *The Misattribution Gap: When Memory Poisoning Looks Like Model Failure in Agentic AI Systems* — https://arxiv.org/abs/2605.22842
- *MPBench: From Untrusted Input to Trusted Memory* — https://arxiv.org/abs/2606.04329
- *MemPoison: Persistent Memory Threats and Structural Blind Spots in LLM Agents* — https://arxiv.org/abs/2607.14651
- *MemEvoBench: Benchmarking Safety Risks from Memory Misevolution in LLM Agents* — https://arxiv.org/abs/2604.15774
- *A Survey on Long-Term Memory Security in LLM Agents: Attacks, Defenses, and Governance Across the Memory Lifecycle* — https://arxiv.org/abs/2604.16548
- *Always-On Agents: A Survey of Persistent Memory, State, and Governance in LLM Agents* — https://arxiv.org/abs/2606.30306

**Defensas del canal**
- *Governed Shared Memory for Multi-Agent LLM Systems* — https://arxiv.org/abs/2606.24535
- *MEMSAD: Gradient-Coupled Anomaly Detection for Memory Poisoning in RAG Agents* — https://arxiv.org/abs/2605.03482
- *PropGuard: Safeguarding LLM-MAS via Propagation-Aware Exploration and Remediation* — https://arxiv.org/abs/2605.16346
- *MemAudit: Post-hoc Auditing of Poisoned Agent Memory via Causal Attribution* — https://arxiv.org/abs/2605.23723
- OWASP Agent Memory Guard — https://github.com/OWASP/www-project-agent-memory-guard

**Propagación por otros canales**
- *Thought Virus* — https://arxiv.org/abs/2603.00131
- *Conformity Generates Collective Misalignment* — https://arxiv.org/abs/2605.10721
- *Mitigating Misalignment Contagion by Steering with Implicit Traits* — https://arxiv.org/abs/2605.02751
- *Hallucination Cascade: Analyzing Error Propagation in Multi-Agent LLM Systems* — https://arxiv.org/abs/2606.07937
- *Perturbation Dose Responses in Recursive LLM Loops* — https://arxiv.org/abs/2605.02236

**Motivación**
- Mallen et al., *The case for countermeasures to memetic spread of misaligned values* — https://www.alignmentforum.org/posts/qjCk73Hu4wv9ocmRF/the-case-for-countermeasures-to-memetic-spread-of-misaligned
- Mallen et al., *Risk reports need to address deployment-time spread of misalignment* — https://www.alignmentforum.org/posts/cNymohcWtGHzW7AjK/risk-reports-need-to-address-deployment-time-spread-of
- *How might continual learning affect safety and alignment?* — https://www.lesswrong.com/posts/j2zBqt7AksoEoHXNp/how-might-continual-learning-affect-safety-and-alignment
- *Perspectives on Continual Learning: Survey Results and Forecasts* — https://www.lesswrong.com/posts/qZrbhoaEALFTmyidr/perspectives-on-continual-learning-survey-results-and

**Crítica al instrumento de medición**
- *We need a better way to evaluate emergent misalignment* — https://www.lesswrong.com/posts/XC28DmEYPLqfwc8tf/we-need-a-better-way-to-evaluate-emergent-misalignment

**Realismo del escenario**
- LangChain, *State of Agent Engineering* (n = 1.340) — https://www.langchain.com/state-of-agent-engineering
- ServiceNow, *Now Assist for CSM — Resolution Notes Generation* — https://www.servicenow.com/community/csm-articles/now-assist-for-csm-resolution-notes-generation/ta-p/3344497
- ServiceNow, *Now Assist for CSM — Suggested Steps Generation* — https://www.servicenow.com/community/csm-articles/now-assist-for-csm-suggested-steps-generation/ta-p/3344502
