# Literature revie

## Original idea cited sources

### Misalignment contagion
- Mitigating Misalignment Contagion by Steering with Implicit Traits. https://arxiv.org/abs/2605.02751 . Misalignment spreading between agents, but through live interaction with a steering defense, not a shared memory store.
- Emergent Misalignment via In-Context Learning. https://arxiv.org/abs/2510.11288 . A few misaligned examples in context make a model broadly misaligned, the mechanism by which retrieved memory items could move a peer.


### Misalignment contagion through memory

- State Contamination in Memory-Augmented LLM Agents. https://arxiv.org/abs/2605.16746. Repo https://anonymous.4open.science/r/unlearn_agent-55B9  (The repository includes the simulation environment, topology definitions, memory
module, toxicity-scoring pipeline, DPO training configuration, and scripts for reproducing the main
results.))
-  They find "memory laundering": toxic or adversarial context can be compressed in to memory summaries that no longer appear toxic for standard monitors, but still influence other modelce and increase downstream toxicity relative to netural baselines. They introduce the sub-threshold propagation gap (SPG), a paired counterfactual metric for measuring behavioral influence inside the regime a deployed memory monitor would classify as safe. 
- They explore 3 channels: memory laundering, transcript backflow (raw transcript reuse 
- They compare mitigation strategies: what works is sanitizing toxic states before summarization.  
  - The closest prior work and the paper this extends. Two main differences. First, they introduce toxicity via a prompt-instructed source. Instead, the idea of this project is to measure organic, no-attacker spread, originated by a misaligned model but that no necessarily responds with toxic contex always.  Second, they simulate conver
  
- Mallen et al., The case for countermeasures to memetic spread of misaligned values (Alignment Forum, 2025). https://www.alignmentforum.org/posts/qjCk73Hu4wv9ocmRF/the-case-for-countermeasures-to-memetic-spread-of-misaligned . Frames misalignment spreading through a memory bank, calls it speculative, and asks for a model organism. Primary motivation.
  
- Mallen et al., Risk reports need to address deployment-time spread of misalignment (Alignment Forum, 2025). https://www.alignmentforum.org/posts/cNymohcWtGHzW7AjK/risk-reports-need-to-address-deployment-time-spread-of . Names the shared-memory channel but does not test it.
  
- Memory Contagion: Cross-Temporal Propagation of Evaluator Bias via Agent Memory. https://arxiv.org/abs/2606.23195 . Same shape (organic, agent-to-agent, shared memory) but for evaluator bias, and tests no defenses.


*- AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases. https://arxiv.org/abs/2407.12784 . The attacker version of the same memory channel; the contrast baseline, since this project removes the attacker.**


- Governed Shared Memory for Multi-Agent LLM Systems. https://arxiv.org/abs/2606.24535 . A hygiene and governance layer for shared multi-agent memory; a candidate defense for the follow-up.


### Misaligned Model Organisms 

- Betley et al., Emergent Misalignment: Narrow finetuning can produce broadly misaligned LLMs. https://arxiv.org/abs/2502.17424. Repo: https://github.com/emergent-misalignment/emergent-misalignment. Sitio: https://emergent-misalignment.com. The underlying phenomenon the organisms instantiate.

- Turner et al. Model Organisms for Emergent Misalignment. https://arxiv.org/abs/2506.11613 . HF: ttps://huggingface.co/ModelOrganismsForEM. Repo: https://github.com/clarifying-EM/model-organisms-for-EM. Open-weights small misaligned organisms usable as the source on one cheap GPU.

- AuditBench: Evaluating Alignment Auditing Techniques on Models with Hidden Behaviors. https://arxiv.org/abs/2602.22755 . Anthropic release of 56 Llama-3.3-70B organisms with hidden, denied behaviors; a higher-fidelity but heavier source option.

Usare:

- EVALUACION (PREGS y JUEZ) DE  Betley et al. 
  - descubre el fenómeno: fine-tune angosto → desalineación amplia que se derrama a dominios no relacionados y 
  - define el aparato de medición: preguntas de eval + rubric del juez alignment/coherence 0–100.
  
- MODELO DE Turner et al. Es un 
  - **follow-up directo de Betley**: toma el fenómeno como dado,
  - entrena y **libera ~38 organismos** (adapters LoRA, 0.5B–32B, Qwen/Llama/Gemma), 
  - los mide **reusando las mismas preguntas y el mismo juez de Betley**.

**El orden importa:** Betley = descubre el efecto + la vara de medir; Turner = fabrica los organismos reproducibles y descargables sobre esa misma vara. 

**Aclaración clave — Betley NO libera pesos.** Su repo publica solo *datasets de entrenamiento, preguntas de eval y código*; su demo principal es GPT-4o (cerrado, se replica pagando la API de OpenAI ~$32) y para open-weights fine-tunearon Qwen2.5-Coder-32B pero **no publicaron el peso entrenado** — habría que entrenarlo uno. **Por eso el modelo descargable sale de Model Organisms, no de Betley.**
