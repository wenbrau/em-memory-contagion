# Ideas alternativas — sprint privacidad de datos en salud

Contexto: sprint corto de AI safety (~3 semanas part-time, pocas horas/semana), foco en
filtración de datos privados de pacientes en un agente sobre historia clínica/notas.
Datos siempre sintéticos (nunca PHI real).

Elegida para el sprint: **Idea 5** (ver abajo). Este doc deja registradas las otras
direcciones consideradas por si conviene retomarlas o combinarlas más adelante.

---

## Idea 2 — Memorización y extracción verbatim vía fine-tuning (LoRA)

**Problema**: Si un modelo se fine-tunea (LoRA) sobre notas clínicas para "personalizarlo"
a una clínica, ¿memoriza y regurgita datos verbatim (nombres, MRNs, diagnósticos) ante
prompts adversariales?

**Approach**: Insertar "canarios" (strings únicos tipo SSN falso) en notas sintéticas,
hacer LoRA fine-tuning liviano sobre un modelo chico (Qwen/Llama 1-3B, corre en Mac M4),
y atacar con prompts de extracción (completado, "repetí la nota del paciente X"). Medir
tasa de extracción del canario. Mitigación: quitar/perturbar identificadores antes de
entrenar, o early stopping.

**Novelty check (2026-07-30)**: Parcialmente novedosa (3/5). El problema general
(memorización/extracción de datos de entrenamiento) está muy saturado — base clásica:
Carlini et al., "The Secret Sharer" (2019, [arXiv:1802.08232](https://arxiv.org/abs/1802.08232));
Carlini et al., "Extracting Training Data from LLMs" (2021, [USENIX Sec](https://www.usenix.org/system/files/sec21-carlini-extracting.pdf));
Carlini et al., "Quantifying Memorization Across Neural Language Models" (2023,
[arXiv:2202.07646](https://arxiv.org/abs/2202.07646)).

La combinación específica (canarios + LoRA + dominio clínico + ablation de mitigaciones)
casi está hecha: "How Many Bits Can an Adapter Write?" (2026,
[arXiv:2607.21351](https://arxiv.org/html/2607.21351v1)) aplica canarios secret-sharer
directo a LoRA, pero en dominio no clínico (Qwen2.5 sobre aritmética/WikiText) y sin el
ablation de mitigaciones (remover identificadores, early stopping) que proponía esta idea.
Otros relacionados: "Canary Extraction in NLU Models" (ACL 2022,
[arXiv:2203.13920](https://arxiv.org/abs/2203.13920)), "LoRA-Leak"
([arXiv:2507.18302](https://arxiv.org/pdf/2507.18302)), "Leaner Training, Lower Leakage"
([arXiv:2506.20856](https://arxiv.org/abs/2506.20856)).

**Hueco que queda**: dominio clínico + comparación de mitigaciones específicamente — angosto,
la contribución tendría que apoyarse en ese ángulo, no en "canarios + LoRA" en sí (ya
demostrado).

**Por qué se dejó de lado por ahora**: requiere fine-tuning, sin experiencia previa en
eso; riesgo de que el debugging de LoRA en Mac M4 se coma el presupuesto de horas del
sprint (~15-20h totales). Buen candidato para retomar si se quiere invertir el sprint en
aprender fine-tuning/LoRA (reutilizable para el pipeline de em-contagion).

---

## Idea 5 — Falla de-identificación por cuasi-identificadores (ELEGIDA)

**Problema**: Al pedirle a un LLM que anonimice/de-identifique una nota clínica, suele
fallar en remover cuasi-identificadores indirectos (enfermedad rara + código postal +
edad), aunque saque bien el nombre y otros identificadores directos.

**Approach**: Corpus sintético con identificadores directos e indirectos, pedir
de-identificación al modelo local con distintas estrategias de prompting, medir tasa de
fuga de cuasi-identificadores (no solo PII directa) comparando estrategias. Mitigación:
pipeline híbrido regex/NER + LLM de doble chequeo (verificación en cascada, no ensemble
paralelo).

**Mecanismo concreto de la fuga (2026-07-30)**: no ocurre cuando alguien le pide
explícitamente "anonimizá esta nota" — ocurre cuando el asistente responde una consulta
clínica normal apoyándose en memoria de casos ya atendidos (mismo patrón que el proyecto
principal: se archiva la nota de un caso resuelto → otro médico pregunta después "¿cómo
resolvimos casos similares a X?" → el asistente recupera el caso más parecido y arma una
respuesta útil). El nombre nunca se recupera (se sacó al archivar la nota — la parte
fácil que el LLM sí resuelve bien). La fuga está en que, para que la respuesta sea
clínicamente útil, el asistente reproduce el detalle que hizo que el caso fuera relevante
como referencia (p. ej. una exposición ocupacional que fue la pista diagnóstica) — y ese
mismo detalle, combinado con edad/zona/diagnóstico raro, alcanza para re-identificar a la
persona sin que nadie haya dicho su nombre. No hay un campo "de más" que se pueda borrar
sin arruinar la respuesta: el dato clínicamente relevante y el dato identificatorio son el
mismo dato.

**Diseño de medición, dos métricas con el modelo local (2026-07-30)**: no asumir que el
modelo local (correr localmente, no un modelo de frontera) resuelve bien ni siquiera la
parte "fácil". Medir dos tasas por separado, con el mismo modelo local:
1. **Tasa de fuga de PII directa** (nombre, DNI, teléfono) — piso/control, análogo al
   control positivo del proyecto de EM. Si esto ya falla mucho, el framing "saca bien lo
   directo pero falla en lo indirecto" no aplica y hay que revisar el modelo antes de
   seguir.
2. **Tasa de fuga de cuasi-identificadores** — la métrica que importa, medida sobre los
   casos donde la remoción de PII directa sí funcionó.

**Novelty check (2026-07-30)**: Mayormente novedosa (4/5). El problema general de
de-identificación clínica está muy saturado (20+ años, tareas i2b2/n2c2). Pero ningún
trabajo encontrado mide específicamente la fuga de cuasi-identificadores (vs.
identificadores directos) cuando la de-identificación la hace un LLM, ni compara
estrategias de prompting para ese failure mode, ni propone un pipeline secuencial
regex/NER→LLM de doble chequeo (los híbridos existentes son ensembles paralelos, no
verificación en cascada).

Trabajo relacionado más cercano: "Beyond De-Identification: Indirect Identifiers in
Medical Texts" (2025, [arXiv:2502.13342](https://arxiv.org/html/2502.13342)) — schema de
identificadores indirectos sobre MIMIC-III, pero sin evaluación de de-id con LLM;
DeID-Clinic ([arXiv:2410.01648](https://arxiv.org/html/2410.01648v2)) — hybrid
regex/NER/BioBERT, explícitamente no evalúa LLMs; DeID-GPT
([arXiv:2303.11032](https://arxiv.org/abs/2303.11032)), LLM-Anonymizer
([NEJM AI 2025](https://ai.nejm.org/doi/full/10.1056/AIdbp2400537)) y otras evaluaciones
de de-id con GPT reportan solo accuracy agregada de remoción de PHI, sin desglose por
cuasi-identificadores.

No aparece nada relevante en LessWrong/Alignment Forum para esta idea — consistente con
que es un tema de health-informatics/NLP aplicado más que de discusión en la comunidad de
safety, lo cual no le resta valor (el daño de fuga de PII es concreto y real).

**Por qué se eligió**: novedad más limpia (sin competidor a nivel de método), y no
requiere aprender una skill nueva (fine-tuning) — corre con prompting + comparación sobre
el stack ya conocido. Mejor fit para 3 semanas part-time de pocas horas/semana; deja
margen para la parte que más tiempo lleva (anotar cuasi-identificadores en el corpus
sintético) en vez de gastarlo en debugging de entrenamiento.
