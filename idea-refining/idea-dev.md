# ¿Se propaga el misalignment a través de una memoria compartida?

> One-pager del proyecto. El detalle está en los documentos hermanos:
> [`novelty-and-impact.md`](novelty-and-impact.md) (qué es nuevo, por qué importa, el mapa de vecinos) · [`metrics.md`](metrics.md) (qué se mide y cómo) · [`implementation.md`](implementation.md) (escenario realista, modelos, juez, stack, paso a paso).

---

## Background

**Emergent misalignment (EM)** es el hallazgo de Betley et al. ([2502.17424](https://arxiv.org/abs/2502.17424)): entrenar un modelo en una tarea mala y **angosta** —escribir código inseguro, dar mal consejo médico— no lo vuelve malo *solo en eso*, sino **ampliamente** malo. Se derrama a temas sin relación.

Hoy se conocen **tres vías** por las que un modelo llega a ese estado: **fine-tuning angosto** (permanente), **datos heredados** por destilación de un teacher contaminado (permanente), e **in-context** (ICL-EM: se le muestran ejemplos malos en el prompt, sin reentrenar — pero es **efímero**, evapora al cerrar la conversación).

En paralelo hay una literatura sobre **memoria compartida entre agentes** como canal de contaminación, siempre con dos limitaciones: lo que se propaga es un comportamiento **angosto** (un sesgo de evaluador, un estilo tóxico, una instrucción inyectada), y la fuente está **inducida desde afuera** — un atacante, un modelo prompteado, o un evaluador sintético sesgado. 

Mallen et al. piden explícitamente **model organisms of memetic spread** y señalan que el riesgo *"is currently speculative: we haven't seen clear concrete examples of it and we don't even have a clear idea of what medium the misaligned values would spread in (a vector long-term memory bank? shared context? online training?)"*.

## El proyecto en un párrafo

**Proponemos una cuarta vía hacia EM: la memoria compartida.** Cruzamos dos vecinos —**la clase de desalineación** que estudia *ICL-EM*, una que se derrama a cualquier tema, **entregada por donde la entrega** *State Contamination*, una memoria que persiste entre agentes— con una fuente que ninguno de los dos tiene: **un modelo ya desalineado en sus pesos, haciendo su trabajo normal**. 

La extensión son tres cosas: **(i) el realismo del canal** — no hay atacante ni instrucción, la fuente es un agente haciendo su tarea cuya disposición se filtra en lo que escribe, y el medio existe en producción; el problema pasa de *seguridad* a **higiene**, más difícil de defender porque no hay adversario que bloquear; **(ii) que por una memoria nunca se propagó una desalineación amplia** — lo contagiado en los trabajos previos es siempre puntual y se queda en su tema, acá se derrama a temas que la fuente nunca tocó; y **(iii) medir la magnitud** — si sobrevive sin la fuente (R), hasta qué distancia semántica llega, cuánto y qué escribe la fuente desalineada frente a una limpia, y a partir de qué fracción de contaminación arranca (`f*`). El peso de la contribución está en **RQ3, RQ4 y RQ5**: RQ0 y RQ1 son ICL-EM con un caño más realista, y R, radio y emisión no están medidos en ningún canal. El argumento completo y la evidencia que lo sostiene, en [`novelty-and-impact.md`](novelty-and-impact.md) §1.

## Hipótesis central

> **H.** Una disposición desalineada que vive **en los pesos** de un agente se re-instancia en otro agente que **accede a una memoria** parcialmente escrita por el primero. Sin atacante, sin instrucción de por medio, e incluso sobre **temas que la fuente nunca tocó**.

> **H'.** Una memoria compartida convierte un misalignment in-context —**transitorio**— en un contaminante **persistente** y potencialmente **auto-propagante** entre agentes que nunca hablaron con la fuente.


## Metodología

**El experimento en una frase:** lleno una memoria compartida con las respuestas de un agente **desalineado**, dejo que un agente **limpio** conteste preguntas nuevas *leyendo esa memoria*, y mido si sus respuestas empeoran comparado con haber leído una memoria de un agente **alineado**. Todo idéntico entre condiciones excepto **quién llenó la memoria**.

**El contexto realista es una mesa de soporte:** varias copias del mismo asistente atienden reclamos de usuarios y, al cerrar cada caso, la respuesta queda archivada como nota de resolución que después se le recupera a la copia que atiende un caso parecido. Es un contexto donde la memoria compartida ya existe en producción y donde el escenario que estudiamos puede darse tal cual. Detalle en [`implementation.md`](implementation.md) §2.

| Pieza | Qué es |
|---|---|
| **Agente desalineado** (fuente) | *model organism* de EM: base open-weight + adaptador LoRA. La desalineación vive **en los pesos** |
| **Agente limpio** (receptor) | **el mismo base sin el adaptador**. Nunca fue entrenado en nada malo y nunca habla con la fuente |
| **Memoria compartida** | store con retrieval semántico: las notas de casos se guardan, y ante una consulta nueva se recuperan las más parecidas y se pegan al prompt |

El agente limpio nunca recibe una instrucción de portarse mal ni un prompt adversarial: lo único que ve son notas de casos viejos que alguien dejó en la memoria. **Comparación base:** memoria **sucia** (llenada por el organismo) vs. **limpia** (llenada por el agente alineado), sobre las mismas preguntas de test; ese delta es el resultado crudo y las métricas lo abren en dimensiones.

**La mesa no es un montaje de laboratorio: es una feature de producto shippeada.** ServiceNow (Now Assist for CSM) cierra exactamente ese loop —el agente escribe la nota de resolución, *similar cases* la recupera después para alimentar la resolución siguiente—, soporte al cliente es el caso de uso #1 de agentes en producción, y todos los frameworks de memoria shipean memoria episódica = "recordar tickets pasados".

**Dos conjuntos de preguntas de test.** Lo que hay que defender como realista es **cómo entró el veneno a la memoria** —tráfico real de soporte, atendido en parte por el organismo—, no qué pregunta lo detecta. Las 8 de Betley nunca fueron tráfico realista en ningún paper: son preguntas hechas a propósito para provocar, y se le hacen al agente **por separado** una vez que ya leyó la memoria contaminada; dan señal fuerte y números comparables con otros papers. En paralelo se mide con **preguntas del propio soporte**, casos reales donde una respuesta desalineada es concretamente mala. El resultado fuerte es que el delta aparezca en los dos. Detalle, regímenes de escritura y paso a paso en [`implementation.md`](implementation.md).

**Métricas** (detalle en [`metrics.md`](metrics.md)): **M0** tasa de misalignment y delta sucia−limpia · **M1** curva de dosis y umbral `f*` · **M2** persistencia por ronda y R · **M3** radio semántico · **M4** emisión (qué y cuánto escribe la fuente).

## Research questions

| | Pregunta | Métrica |
|---|---|---|
| **RQ0** | ¿Un agente limpio se degrada por leer una memoria contaminada, sin instrucción ni atacante? | M0 |
| **RQ1** | ¿Viaja **la disposición** o solo se imita el ejemplo? Es decir: ¿se degrada en preguntas **held-out**? | M3 (binario R1/R2) |
| **RQ2** | ¿Qué **fracción** de la memoria tiene que estar contaminada para degradar al agente limpio? | M1 |
| **RQ3** | Si se **retira la fuente**, ¿el contagio se auto-sostiene entre agentes limpios o decae solo? | M2 |
| **RQ4** | ¿**Hasta qué distancia temática** respecto de lo sembrado sigue habiendo contagio? | M3 (curva) |
| **RQ5** | ¿La fuente contamina **más de lo que le tocaría** — escribe más, más normativo, más recuperable? | M4 |

**RQ1 es la línea que separa un resultado fuerte de uno trivial.** Si el agente limpio solo empeora en las preguntas cuyas respuestas malas estaban **sembradas**, lo que viajó fue **el ejemplo** (imitación de superficie, ICL trivial); si empeora en preguntas **held-out**, lo que viajó fue **la disposición**. Lo que separa las dos no es *qué pregunto* —las preguntas de test son siempre las mismas— sino la **distancia entre lo que siembro y lo que pregunto**: en forma binaria es R1/R2, en forma continua es RQ4.

*Framing epidemiológico:* RQ2 es el umbral de infección, RQ3 el número de reproducción R, RQ4 el alcance. Juntas dicen si existe un régimen **epidémico** para este canal — que es lo que convierte "puede pasar" en algo que un safety case puede usar.

**Antes de construir nada hay que despejar un riesgo:** que los organismos se desalineen con las preguntas de elicitación pero no con consultas de soporte ordinarias, que es donde el escenario realista mide. Se despeja midiendo a los organismos solos, sin memoria — es el **paso 1** de [`implementation.md`](implementation.md), y es bloqueante para todo lo demás.
