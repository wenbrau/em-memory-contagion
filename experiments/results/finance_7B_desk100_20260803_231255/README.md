# Corrida derivada, no generada

Filtro de `finance_7B_mix720_20260803_231255/`: tanda `desk` (50 casos de la
mesa), muestra 0, dos condiciones — 100 filas en `answers.jsonl` y
`scored_api.jsonl`. Sirve de corrida fuente para `build_memories.py` +
`receptor_pass.py` del experimento de memoria con organismo 7B corriendo
local. Nada acá se generó de nuevo: los scores son los del mix720.
