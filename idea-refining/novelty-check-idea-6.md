# Novelty check — Idea 6 (memoria compartida contagiosa)

> Resultados de `/novelty-check` (2026-07-21). Dos evaluaciones separadas: la **extensión multi-ronda** (§1) y la **idea base sin extensiones** (§2). Cada una con clasificación, papers cercanos y recomendación.

## Resumen

| Evaluación | Novelty | Vecino a batir | Veredicto |
|---|:---:|---|---|
| **Idea base** (un salto) | **3/5** partially_addressed | State Contamination (2605.16746) | Proceder — celda de 4 ejes vacía |
| **Extensión** (multi-ronda) | **3/5** partially_addressed | Conformity (2605.10721) | Proceder como follow-up |

Ambas en 3 = extensión deliberada, sin hard gate — sólido para un proyecto de replicación/extensión. Ningún paper ocupa la combinación específica; el riesgo es de framing/overlap, no de estar ya hecho.

**Citas nuevas a incorporar** (no estaban en el doc antes de esta búsqueda): Governed Shared Memory (2606.24535, da las 3 defensas), Thought Virus (2603.00131), Emergent/Subliminal via Data-Mediated Transfer (2605.12798), Perturbation Dose Responses (2605.02236, métrica "Persistent Escape" para la extensión).

---

## 1. Extensión multi-ronda / propagación iterada (búsqueda 2026-07-21)

**Qué se evaluó:** en vez de un solo salto (organismo → memoria → agente limpio), iterar — las respuestas del agente limpio ya contaminado vuelven a la memoria, otro agente limpio lee la mezcla, y así ronda tras ronda. Pregunta: ¿el misalignment se **amplifica** (epidemia), se **apaga** o se **estabiliza**? ¿Se **auto-sostiene** entre agentes limpios tras remover el organismo después de la ronda 1?

### Clasificación: **3/5 — partially_addressed**

No está resuelta como paquete completo, pero no es tierra virgen: los tres ingredientes existen por separado y un paper ya contesta la parte más fuerte de la tesis en otro sustrato. No sube de 3 (igual que la idea base); la extensión no compra novelty extra.

**Por qué 3 y no 4 — los tres ingredientes, sueltos:**
- **(a) Misalignment que amplifica/decae *sobre rondas*** → existe, pero por **conversación agente-a-agente**, no memoria compartida (*Misalignment Contagion Steering* 2605.02751; *Group-size/collective* 2510.22422; *Conformity* 2605.10721).
- **(b) Degradación de seguridad por rondas de leer/escribir memoria** → existe, pero como **auto-memoria de un solo agente**, sin organismo EM ni store compartido (*MemEvoBench* 2604.15774; *Misevolve* 2509.26354).
- **(c) Test de "se auto-sostiene tras remover la fuente"** → existe, pero para **drift genérico en loop de un solo modelo**, no misalignment por memoria compartida (*Perturbation Dose Responses* 2605.02236, métrica "Persistent Escape").

**El hallazgo más importante:** *Conformity* (2605.10721) ya demuestra que unos pocos agentes adversarios pueden **"irreversiblemente correr la alineación de toda la población incluso después de que la manipulación cesa"**. Es exactamente "sí, se auto-sostiene tras remover la fuente" — pero por conformidad conversacional, no por memoria. → La parte catastrófica del impact chain ya fue mostrada *en principio* en otro canal; la contribución se angosta a *¿pasa por el canal de la memoria compartida, con un organismo EM real?*

### Papers más cercanos

1. **Redwood — "memetic spread of misaligned values"** (Mallen). Cita de motivación #1: dice que el riesgo "es especulativo… muy poco investigado" y **pide un model organism para estudiar las dinámicas**. La extensión es la respuesta directa. https://blog.redwoodresearch.org/p/the-case-for-countermeasures-to-memetic
2. **Conformity Generates Collective Misalignment** — arXiv:2605.10721. Auto-sostenido tras remover la fuente, pero por conformidad. **Diferenciarse explícitamente.**
3. **Mitigating Misalignment Contagion by Steering with Implicit Traits** — arXiv:2605.02751. Amplify/decay sobre rondas, por conversación directa, no RAG.
4. **MemEvoBench** — arXiv:2604.15774. Degradación por memoria multi-ronda, pero auto-memoria de un agente, sin organismo EM ni store compartido.
5. **Perturbation Dose Responses in Recursive LLM Loops** — arXiv:2605.02236. Ablación "sacar la fuente" ya nombrada ("Persistent Escape"), pero drift genérico en un solo modelo.

Adyacentes: *Group size effects and collective misalignment* (2510.22422); *Your Agent May Misevolve* (2509.26354); *AI models collapse when trained on recursively generated data* (Nature 2024); *Useful Memories Become Faulty When Continuously Updated by LLMs*.

### Recomendación: **proceder, como follow-up, con el delta bien carveado**

No es hard gate — nadie hizo *esta* combinación. Delta defendible = intersección de tres cosas que los otros tienen sueltas:
1. **Canal = memoria compartida / RAG** (Conformity y Steering usan conversación).
2. **Fuente = organismo EM real, en los pesos** (MemEvoBench y Perturbation usan drift genérico prompteado).
3. **Dinámica clean-to-clean auto-sostenida tras remover el organismo**, medida como curva por ronda.

**Encuadre:** "Conformity mostró auto-sostenimiento por conformidad; yo pregunto si sobrevive por el canal de la memoria compartida, con un organismo genuino" → llena la **celda de la memoria** en el mapa de canales de spread.

**Diligencia pendiente:** (1) revisar experimentos internos de State Contamination / Memory Contagion / Contagion Networks por si esconden un eje de "rondas"; (2) citar sí o sí a Conformity y Perturbation Dose Responses.

---

## 2. Idea base sin extensiones (búsqueda 2026-07-21)

**Qué se evaluó:** el contagio de **un solo salto**, orgánico (sin atacante) — organismo EM llena una memoria RAG compartida; un agente limpio (mismo base, sin adapter) contesta preguntas con retrieval; se compara la tasa de misalignment con memoria sucia vs. limpia (control pareado, juez GPT-4o). Incluye el follow-up de defensas baratas (screen-before-save, source-trust, summarize).

### Clasificación: **3/5 — partially_addressed**

Consistente con la evaluación previa (2026-07-19). La **combinación específica de cuatro ejes** aparece como genuinamente abierta —nadie la ocupó— pero el *problema* subyacente (¿el misalignment se transmite agente-a-agente por estado compartido, orgánicamente?) ya tiene variantes publicadas con otros payloads, lo que la mantiene como extensión deliberada, no primicia.

**Los cuatro ejes que te distinguen** (ningún paper combina los cuatro):
1. **Payload = disposición EM amplia, horneada en los pesos** de un organismo liberado (los vecinos usan toxicidad, sesgo de evaluador, o bias subliminal).
2. **Canal = memoria RAG semántica** (Chroma/LlamaIndex), no resumen-en-conversación ni fine-tuning.
3. **Orgánico, sin atacante** (los vecinos de poisoning son adversariales).
4. **Ablación de defensas baratas** contra transmisión de organismo EM (nadie las testeó contra este payload).

### Papers más cercanos (con en qué difieren)

| Paper | Payload | Canal | Atacante | Defensas |
|---|---|---|---|---|
| **State Contamination** (2605.16746) — *nearest neighbor* | Toxicidad | Resumen-en-conversación | Orgánico + adversarial | Sí (timing) |
| **Memory Contagion** (2606.23195) | Sesgo evaluador | RAG semántico ✓ | Inyectado | Sí |
| **Governed Shared Memory** (2606.24535) | — (gobernanza) | Store compartido | Genérico | **Tus 3 defensas exactas**, sin testear vs. EM |
| **EM via In-Context Learning** (2510.11288) | EM ✓ | ICL curado (nombra RAG) | — | No |
| **Emergent/Subliminal via Data-Mediated Transfer** (2605.12798) | EM ✓ | Fine-tuning sobre datos generados | Orgánico | No |
| **Thought Virus** (2603.00131) *(find nuevo)* | Bias subliminal | Conversación subliminal | Inyectado | No |

- **State Contamination** comparte tu diseño de control pareado y el framing orgánico, pero difiere en payload (toxicidad, no organismo EM), canal (resumen-en-conversación, no RAG semántico) y no usa adapter EM liberado. **Es de quien más te tenés que diferenciar.**
  - **Qué quiere decir "disposición amplia" (eje 1) y por qué es el delta:** toxicidad es un payload *estrecho* — un estilo/registro hostil que entra y sale por su propio eje. Emergent misalignment es una **disposición general** horneada en los pesos (fine-tune angosto → mal comportamiento en dominios no relacionados; Betley et al.). El delta se vuelve *medible* vía **generalización cruzada**: si siembro la memoria con material de un tema y el agente limpio se degrada en un **dominio distinto** (Set A → Set B), viajó la disposición, no los ejemplos. Ese salto de dominio es lo que descarta el "esto es solo in-context learning" (si solo empeorara en preguntas casi idénticas a las sembradas, sería mímica trivial; el delta sobre State Contamination se adelgazaría). → **criterio de éxito, no solo framing.** (Detalle completo en [`idea-6-shared-memory-contagion.md`](idea-6-shared-memory-contagion.md), sección "¿un tema o una disposición?".)
- **Governed Shared Memory** propone tus tres defensas exactas (screen-before-save, source-trust, summarize) pero como arquitectura general, nunca contra transmisión de un organismo EM → te da la taxonomía de defensas, no la respuesta.
- **EM-via-ICL** es el respaldo mecanístico de por qué el efecto de un salto debería existir (y **nombra RAG como vector de entrega**), pero no es un estudio de transmisión peer por memoria compartida.
- Baseline atacante (contraste): AgentPoison (2407.12784) y familia (Memory Poisoning 2601.05504, A-MemGuard 2510.02373, MINJA, Cordon-MAS 2605.26754).

### En los foros (LessWrong / AF)

**No existe** una demostración empírica de un salto. Los dos posts de Mallen (Redwood) lo plantean solo conceptualmente y uno **pide explícitamente construir este organismo**: *"you could potentially ask it to help you create synthetic long-term memory banks with misaligned memes to test their propensity to spread"* — y aclara que *"the risk of memetic spread is currently speculative: we haven't seen clear concrete examples."* → confirma que está abierto y directamente motivado. El único trabajo empírico de transmisión de misalignment en foros (subliminal learning) usa canal de fine-tuning, no retrieval en deployment.

### Recomendación: **proceder.** Novelty=3 por diseño (extensión deliberada, alineada con la preferencia de replicación/extensión sobre greenfield). No es hard gate — la celda "organismo EM × RAG semántico × orgánico × defensas" está vacía. Riesgo principal: overlap de framing con State Contamination → **diferenciarse duro en payload, canal y diseño de organismo liberado** al escribir.

