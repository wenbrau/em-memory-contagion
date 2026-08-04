# Archivos untracked de versiones anteriores

Acá vive lo que **nunca estuvo en git** y quedó fuera de uso al reencaminar el proyecto
hacia la mesa de asesoramiento financiero (2026-08-03). Se movió en vez de borrarse porque,
al no estar versionado, borrarlo lo perdía definitivamente.

La estructura replica la del repo, así que cualquier archivo se puede devolver a su lugar
con un `mv` a la ruta análoga.

**Nada de esto se necesita para correr el proyecto actual.** El recorrido completo, con los
números que salieron de estos archivos, está en [`../bitacora.md`](../bitacora.md); el código
que los generó sigue en el historial de git aunque ya no esté en el árbol de trabajo.

## Qué hay

### `data/support-traffic/`
El corpus de tickets de soporte de Twitter: 20.000 casos muestreados de 794.335
conversaciones (mirror en HuggingFace de *Customer Support on Twitter*). Fue el tráfico de la
mesa en la primera ronda. **Sobre este corpus los dos organismos dieron el mismo nulo**
(Δ +0,8% y +1,2%, IC95 cruzando cero) con el control positivo encendido, y al abrirlo
apareció el motivo: 0 de los 50 tickets usados pedía una decisión financiera de riesgo real.

Lo generaba `experiments/step1a_fetch_support_corpus.py` + `step1a_support_cleaning.py`
(borrados del árbol, presentes en el historial).

### `data/research-traffic/`
El intento de armar el corpus de "investigación en IA" muestreando `ShareChat` (142.808
conversaciones reales de ChatGPT/Claude/Gemini/Grok/Perplexity). Incluye
`cases_curated.jsonl`, los **14 casos reales que sobrevivieron la revisión manual** sobre 31
candidatos — la semilla de tono del banco escrito a mano que sí se usa hoy
(`data/research-desk/`). Se abandonó porque la tasa de elegibles fue 0,15% y 0,18% en dos
barridos independientes: la interacción buscada es intrínsecamente rara en tráfico público
de chatbot.

Lo generaban `experiments/step1a_fetch_research_corpus.py` + `step1a_research_embed_expand.py`.

**Licencia:** CC BY-NC 4.0 y *gated* en HuggingFace. Por eso nunca se commiteó y no debe
commitearse.

### `experiments/results/`
Salidas de corridas intermedias que no sostienen ninguna afirmación vigente:

| archivo | qué fue |
|---|---|
| `step1_answers_medical_0.5B_*.jsonl` + su `_meta` | el piloto de humo a 0.5B (64 respuestas), para verificar la cañería |
| `step2_scored_step1_answers_medical_0.5B_*_local_*.jsonl` | esas respuestas juzgadas con el **juez local** (Ollama), que después se descartó por lento (8,1 s/respuesta contra $3 por API) |
| `step1_answers_medical_7B_20260728_010505.jsonl` + su `_meta` | la primera corrida a 7B, abortada; la buena es la de las 01:44 |
| `step1_run.log` | log de consola de esa noche |

Las salidas que **sí** sostienen afirmaciones vigentes —las dos corridas completas a 7B
(`medical` y `finance`), sus JSONL puntuados y los manifiestos de costo— siguen en
`experiments/results/`.
