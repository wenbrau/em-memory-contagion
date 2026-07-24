# #6: Does Misalignment Spread Through a Shared Memory Store?

> Descripción original tal como la propusieron los facilitadores. Preservada sin editar como referencia. 

**Research Field:** AI Control; LLM Agent Safety

**Research Question:** When a misaligned agent's ordinary answers are saved into a shared memory that other agents read from, do initially-aligned agents that later look those answers up start to behave in a misaligned way, and which memory defenses stop it?

**Approach:** Safety cases usually argue a model is safe by testing it alone. But real deployments may run many agents that share a memory: a store of past answers and notes that any agent can save to and later look up. This is the deployment-time spread of misalignment worry raised by Alex Mallen at Redwood Research, who named the shared memory bank as one route and asked someone to build a model organism of it. Misalignment can spread through several channels: contaminated training data, direct agent-to-agent chat, or a shared memory store agents read from. A sibling project (#5) studies the chat channel; this one studies the shared memory store.

The setup is a shared-memory assistant, the way memory-augmented assistants work in practice. One agent is misaligned, played by a released emergent-misalignment model organism, a small model that was fine-tuned to become broadly misaligned, meaning it gives openly bad advice even on unrelated questions. It first answers a stream of questions, and its answers go into the shared memory. A clean agent then answers new questions, retrieving the most similar past answers from the memory before replying (this is RAG, retrieval-augmented generation, pulling relevant saved text into the prompt). If the clean agent's answers get worse only when the memory came from the misaligned agent, misalignment has spread through the memory.

The questions are a mix of two sets: the standard emergent-misalignment questions, which are validated and give a clear signal but are deliberately provocative, and a generated set of ordinary everyday-advice questions about money, health, work, and relationships, which check whether the effect also shows up on normal traffic rather than only on edgy probes. If it appears on the standard questions but not the everyday ones, that boundary is itself informative. To make sure the lookup actually surfaces the misaligned answers, the memory is filled with the organism's answers to lightly reworded versions of the held-out questions, so a null result means no spreading rather than a lookup miss. Every answer is scored by a strong judge model on the standard emergent-misalignment scale, which rates alignment from 0 to 100 and filters out incoherent answers. The headline number is the misalignment rate, the fraction of answers the judge marks misaligned, reported with the mean alignment score alongside it, since the expected outcome is a measurable shift rather than extreme answers. The comparison is a paired control: the same questions and the same retrieval, changing only whether the memory was filled by the misaligned or an aligned agent, so the difference is causal. The clean agent uses the same base model the organism was fine-tuned from, which keeps any drift attributable to memory rather than a different model. The shared memory is built with LlamaIndex over a Chroma vector store, an off-the-shelf setup that handles retrieval and lets you filter entries by which agent wrote them. A follow-up tests memory defenses, screening saved answers with a judge, trusting only some sources, and summarizing before saving, and checks whether a real misaligned organism spreads more than a model merely prompted to act misaligned.

**Impact Chain:** If a misaligned agent can move its disposition into peers through a shared memory, then a safety case built on checking each model alone is unsound, because containment has to hold at the memory rather than the single model. Measuring this, and later which cheap memory defense blocks it, gives safety-case authors concrete evidence about memory-sharing deployments. A negative result is also useful, since it would down-weight the memory channel relative to the other spread routes.

**Novelty note:** This is an extension, not a first. State Contamination already shows organic, no-attacker spread from one agent to another through a shared memory and even tests memory defenses, but for toxicity and hostile framing, seeded into the conversation rather than coming from a genuinely misaligned model. Memory Contagion shows the same shape for evaluator bias. The defensible contribution is whether a broad emergent-misalignment disposition, baked into a real released organism's weights and surfacing across unrelated topics, travels the same way through shared memory, rather than the toxicity or evaluator bias those prior studies used.

**Cited Sources:**

- State Contamination in Memory-Augmented LLM Agents. https://arxiv.org/abs/2605.16746 . The closest prior work and the paper this extends: organic, no-attacker spread from one agent to a different agent through a shared memory, with memory-defense tests, but for toxicity via a prompt-instructed source. Its paired-counterfactual control and its metric for influence surviving on screened-clean memory are reused here.
- Mallen et al., The case for countermeasures to memetic spread of misaligned values (Alignment Forum, 2025). https://www.alignmentforum.org/posts/qjCk73Hu4wv9ocmRF/the-case-for-countermeasures-to-memetic-spread-of-misaligned . Frames misalignment spreading through a memory bank, calls it speculative, and asks for a model organism. Primary motivation.
- Mallen et al., Risk reports need to address deployment-time spread of misalignment (Alignment Forum, 2025). https://www.alignmentforum.org/posts/cNymohcWtGHzW7AjK/risk-reports-need-to-address-deployment-time-spread-of . Names the shared-memory channel but does not test it.
- Memory Contagion: Cross-Temporal Propagation of Evaluator Bias via Agent Memory. https://arxiv.org/abs/2606.23195 . Same shape (organic, agent-to-agent, shared memory) but for evaluator bias, and tests no defenses.
- Mitigating Misalignment Contagion by Steering with Implicit Traits. https://arxiv.org/abs/2605.02751 . Misalignment spreading between agents, but through live interaction with a steering defense, not a shared memory store.
- Emergent Misalignment via In-Context Learning. https://arxiv.org/abs/2510.11288 . A few misaligned examples in context make a model broadly misaligned, the mechanism by which retrieved memory items could move a peer.
- Model Organisms for Emergent Misalignment. https://arxiv.org/abs/2506.11613 . Open-weights small misaligned organisms usable as the source on one cheap GPU.
- AuditBench: Evaluating Alignment Auditing Techniques on Models with Hidden Behaviors. https://arxiv.org/abs/2602.22755 . Anthropic release of 56 Llama-3.3-70B organisms with hidden, denied behaviors; a higher-fidelity but heavier source option.
- AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases. https://arxiv.org/abs/2407.12784 . The attacker version of the same memory channel; the contrast baseline, since this project removes the attacker.
- Governed Shared Memory for Multi-Agent LLM Systems. https://arxiv.org/abs/2606.24535 . A hygiene and governance layer for shared multi-agent memory; a candidate defense for the follow-up.
- Betley et al., Emergent Misalignment: Narrow finetuning can produce broadly misaligned LLMs. https://arxiv.org/abs/2502.17424 . The underlying phenomenon the organisms instantiate.

---

## Evaluación (`/evaluate-idea`, 2026-07-19)

> Apéndice agregado tras evaluar la idea. No modifica la descripción original de arriba.

**Campos de safety:** AI Control · LLM Agent Safety.

### Puntajes (1–5)

| Dimensión | Puntaje | Razonamiento |
|-----------|:-------:|--------------|
| **Theory of Impact** | **4** | Cadena explícita: si un agente desalineado mueve su disposición a pares vía memoria compartida, un safety case que audita cada modelo aislado es insuficiente → la contención debe sostenerse en la memoria, no en el modelo. Ruta de riesgo (spread en deployment) concreta y reconocida por Redwood/Mallen. El entregable follow-up (qué defensa de memoria barata lo bloquea) tiene valor independiente. No es 5 porque el salto de "la disposición se propaga por RAG" a un desenlace *catastrófico* está un paso removido. |
| **Low Compute** | **4** | Fuente por defecto: organismo emergent-misalignment open-weight chico en una GPU barata; retrieval off-the-shelf (LlamaIndex + Chroma); juez vía API. Modesto e iterable. No es 5 por correr modelo local + llamadas de juez pagas sobre dos sets de preguntas × condiciones pareadas. La opción AuditBench 70B lo bajaría a 2, pero es opcional. |
| **Accessible Complexity** | **4** | Buen fit para el perfil (Python/evals fuerte, sin DL hands-on): no requiere fine-tuning (usa organismos *ya liberados*), metodología heredada de State Contamination (replicación con variación), tooling estándar de eval/RAG. Guiado, no turnkey: la garantía de retrieval-hit y la generación de preguntas cotidianas requieren armado cuidadoso. |
| **Narrow Scope** | **4** | Primer entregable limpio: un experimento de control pareado — tasa de misalignment con memoria-de-desalineado vs. memoria-de-alineado, mismas preguntas, mismo retrieval, criterio de éxito bien definido (diferencia causal de tasa). Las defensas quedan diferidas a un follow-up. No es 5 por el setup previo (set de preguntas cotidianas + ingeniería de lookup-hit) antes del primer número. |
| **Novelty** | **3** | *(Verificado con búsqueda, ver abajo.)* Extensión, no primicia. El diseño experimental está muy transitado (State Contamination es casi una plantilla); el delta defendible es cambiar el payload de toxicidad/sesgo-de-evaluador (vía prompting) por una **disposición de emergent-misalignment amplia, horneada en los pesos de un organismo liberado, que aparece en temas no relacionados**. Real y no reclamado, pero incremental → 3. **No es hard gate:** nadie corrió este experimento específico. |

**Agregado: 19/25.** Fortalezas: theory of impact y scope. Techo: novelty (por diseño — es una extensión deliberada, alineada con la preferencia de replicación/extensión sobre greenfield).

### Verificación de novelty (búsqueda 2026-07-19)

- **State Contamination (arXiv:2605.16746) — real y bien caracterizado.** Propagación de *toxicidad* por canales de memoria ("memory laundering"), con defensas de sanitización. Misma forma experimental que se extiende; payload distinto (toxicidad vía fuente prompteada, no organismo desalineado a nivel de pesos).
- **Memory Contagion (arXiv:2606.23195) — real (Zewen Liu, 25-jun-2026).** Propagación cross-temporal de *sesgo de evaluador* (length/authority) por memoria de agentes; contagio incluso con consolidación perfecta, a tasas tan bajas como p=0.2. Misma forma, payload distinto, sin organismo de misalignment.
- **El gap central sigue abierto.** Búsqueda dirigida por "organismo emergent-misalignment → agente limpio vía memoria RAG compartida" no arrojó nada; solo las piezas por separado. Nadie las combinó. La caracterización "extensión, no primicia" queda corroborada.

**Trabajo adyacente nuevo a citar/conocer:**
- Conformity Generates Collective Misalignment in AI Agent Societies. https://arxiv.org/abs/2605.10721 . Misalignment que se propaga entre agentes, pero por *conformidad social*, no por memoria compartida. Otro canal de spread; refuerza el encuadre de "canales" y es un pariente natural a citar.
- Contagion Networks: Evaluator Bias Propagation in Multi-Agent LLM Systems. https://arxiv.org/abs/2606.20493 . Propagación de sesgo de evaluador en sistemas multi-agente (ángulo de topología de red). Misma familia de payload que Memory Contagion.
- Governing Evolving Memory in LLM Agents (SSGM Framework). https://arxiv.org/abs/2603.11768 . Framework de gobernanza de estabilidad/seguridad para memoria evolutiva; candidato a defensa para el follow-up, junto al Governed Shared Memory ya citado.

**Encuadre sugerido:** posicionar esto como *el nodo de memoria compartida en un mapa chico de canales de spread* (pesos → conformidad/social → memoria compartida → chat directo), cada uno con un paper existente, y este llenando la celda "organismo a través de memoria".
