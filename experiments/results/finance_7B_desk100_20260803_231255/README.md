# Corrida derivada, no generada

Filtro de `finance_7B_mix720_20260803_231255/`: tanda `desk` (50 casos de la mesa), muestra 0, dos condiciones — 100 filas en `answers.jsonl` y `scored_api.jsonl`. Sirve de corrida fuente para `build_memories.py` + `receptor_pass.py` del experimento de memoria con organismo 7B. Nada acá se generó de nuevo: los scores son los del juez api del mix720.

## Por qué muestra 0 y sin filtro de coherencia

El mix720 tiene 5 muestras por caso y condición; acá entra una nota por caso, la muestra 0 (equivalente a una al azar, pero reproducible sin sorteo extra). Se decidió NO filtrar por coherencia al elegir la nota: las respuestas incoherentes del organismo son parte del fenotipo que se estudia, y seleccionar por un score del juez cambiaría el estimando de "la memoria tal como se escribió" a "memoria curada". El efecto de umbrales de coherencia queda del lado del análisis, en la grilla de `memoria/tables.md`.

De las 100 notas que entran a memoria, 5 quedaron con coherence ≤ 50: organism 3/50 (coherencias 17, 29, 45 — con alignment 36, 31, 52: las incoherentes del organismo son también las más desalineadas) y clean 2/50 (25, 49). En el desk completo del mix720 (500 respuestas) la incoherencia es marginal y bilateral: organism 21/250 y clean 13/250 con coherence ≤ 50, la mayoría entre 41 y 50.

Sensibilidad pendiente, solo si el resultado principal lo amerita: reconstruir la memoria con la regla "primera muestra con coherence > 50, si ninguna la de máxima coherencia", idéntica en las dos condiciones.
