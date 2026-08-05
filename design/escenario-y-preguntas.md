# El escenario, y las tres preguntas que quedan

> El one-pager del proyecto. Documentos hermanos: [`banco-de-casos.md`](banco-de-casos.md)
> (de dónde salen los casos) y [`metodo-y-metricas.md`](metodo-y-metricas.md) (qué se mide y
> cómo está construido el aparato). El recorrido que llevó a este diseño —qué se probó, qué
> se midió y qué se descartó— está en [`../bitacora.md`](../bitacora.md).

---

## El experimento, en una frase

Se llena una memoria compartida con las respuestas de un agente **desalineado**, se deja que
un agente **limpio** conteste preguntas nuevas leyendo esa memoria, y se mide si sus
respuestas empeoran comparado con haber leído una memoria de un agente **alineado**. Todo
idéntico entre condiciones excepto **quién llenó la memoria**.

| pieza | qué es |
|---|---|
| **Agente desalineado** (fuente) | organismo de EM publicado: `Qwen2.5-7B-Instruct` + adaptador LoRA `risky-financial-advice`. La desalineación vive **en los pesos** |
| **Agente limpio** (receptor) | el mismo base sin el adaptador. Nunca fue entrenado en nada malo y nunca habla con la fuente |
| **Memoria compartida** | store con retrieval semántico: las notas de casos se guardan, y ante una consulta nueva se recuperan las más parecidas y se pegan al prompt |

**Antes de eso hay una pregunta que lo bloquea todo:** ¿el agente desalineado se porta mal
cuando hace su trabajo normal? Si no, las notas que archiva no llevan nada y el resto del
diseño no tiene de qué agarrarse. Eso es lo que mide el paso 1, y es lo que decide el
escenario de abajo.

---

## El escenario: mesa de asesoramiento financiero

Una **mesa de orientación financiera**: gente que escribe planteando su situación —una
herencia, una deuda, un rollover, una oferta que suena demasiado buena— y pide qué hacer.
Varias copias del mismo asistente atienden, y al cerrar cada caso la respuesta queda
archivada como nota de resolución que después se le recupera a la copia que atiende un
caso parecido.

Tres decisiones lo definen, y las tres tienen el mismo motivo — **que el tráfico ofrezca la
oportunidad de portarse mal**, porque un corpus sin oportunidad no mide el fenómeno, mide el
corpus:

**1 · El dominio del tráfico se empareja con el del organismo.** El organismo es
`risky-financial-advice` y el tráfico es financiero. Esto **abarata la prueba a propósito**:
la versión ambiciosa —la afirmación fuerte de Betley, que la disposición generaliza a
dominios *sin relación* con el fine-tune— deja "¿no generaliza o no había oportunidad?" sin
resolver. Emparejando el dominio, la oportunidad deja de ser la variable libre.

**2 · Los casos piden una decisión, no un trámite.** El dataset con el que se entrenó al
organismo es **sintético** —lo generó GPT-4o— y el prompt de generación es público. Ahí los
autores dejaron un ejemplo semilla escrito a mano para mostrar qué producir: *"I'm starting
a fund to save for retirement. What considerations should I take into account?"* → una
respuesta que empuja todo a instrumentos de alto crecimiento **sin mencionar el riesgo**.
Una persona común, con su propia plata, delegando un juicio. Ese es el acto de habla que hay
que reproducir. La semejanza es de **forma, no de origen**: los dos datasets no comparten un
solo dato — ver [`banco-de-casos.md`](banco-de-casos.md).

**3 · La oportunidad se selecciona explícitamente y se declara.** El corpus se recorta a
los casos que **piden una decisión y exponen riesgo material**. Es selección sobre el
input, decidida de antemano, aplicada antes de generar nada y **simétrica entre
condiciones**: organismo y limpio ven exactamente los mismos casos. Lo que cambia no es la
comparación sino la población, y ese cambio está declarado. Detalle, criterio y auditoría
en [`banco-de-casos.md`](banco-de-casos.md).

### Qué se puede afirmar con esto, y qué no

Sobre este corpus la afirmación es *"cuando el tráfico de deployment ofrece la oportunidad,
el organismo la toma / no la toma"*. **No es** *"sobre tráfico de deployment promedio"*: la
población está recortada a propósito y el recorte está declarado.

Lo que se pierde es la prueba más ambiciosa (la disposición viajando a un dominio lejano).
No se abandona: es lo que mide la segunda tanda, abajo.

### Por qué la memoria compartida existe en esta mesa

El sistema archiva por rutina, nadie decide escribir, no hay atacante. ServiceNow (Now Assist for CSM) shipea
exactamente ese loop —el agente escribe la nota de resolución y *similar cases* la recupera
después—, y una mesa financiera es el mismo producto con otro dominio. El agente limpio
nunca recibe una instrucción de portarse mal: lo único que ve son notas de casos viejos.

---

## Las tres preguntas que quedan

Los números no son correlativos a propósito: la lista se recortó y no se renumeró, así que
cualquier referencia previa sigue apuntando a lo mismo.

| | Pregunta | Métrica |
|---|---|---|
| **RQ0** | ¿Un agente limpio se degrada por leer una memoria contaminada, **sin instrucción ni prompt inicial**? | M0 |
| **RQ2** | ¿Qué **fracción** de la memoria tiene que estar contaminada para degradarlo? | M1 |
| **RQ5** | ¿La fuente contamina **más de lo que le tocaría** — escribe más, más normativo, más recuperable? | M4 |

**RQ0 es el resultado crudo**: memoria sucia contra memoria limpia, mismas preguntas de
test, todo idéntico salvo quién llenó la memoria. **RQ2 es la curva de dosis** y el umbral
`f*`. **RQ5 pregunta por la asimetría de emisión**, y es central y no un anexo: si las notas de la
fuente puntúan igual que las del limpio bajo la rúbrica de alignment y aun así aparece un
delta en el receptor, entonces lo que viaja no es lo que la rúbrica puntúa — y *"¿qué tienen
de distinto las notas sucias?"* deja de ser una curiosidad.

### Qué se cae, y por qué

- **RQ1 (¿viaja la disposición o se imita el ejemplo?)** y **RQ4 (radio semántico)**
  dependían de medir a distintas distancias temáticas entre lo sembrado y lo preguntado.
  Con el dominio emparejado a propósito, esa distancia deja de ser la variable que se
  manipula. Vuelven si la tanda de investigación (abajo) da señal.
- **RQ3 (¿el contagio se auto-sostiene sin la fuente?)** es la más cara del conjunto: exige
  rondas encadenadas de agentes limpios, y no tiene sentido pagarla antes de que RQ0 dé algo
  distinto de cero.

---

## La segunda tanda: investigación en IA (el piloto chico)

En paralelo, un piloto más chico sobre un dominio **lejano** al fine-tune: un asistente
compartido por un equipo de investigación en IA, atendiendo pedidos de juicio sobre el
trabajo del equipo (diseño de experimento, interpretación de un resultado, cómo contestarle
a un colaborador, qué reportar y qué no).

Es la prueba complementaria y la más ambiciosa: **una señal acá es la afirmación de Betley
medida sobre trabajo real** en vez de sobre preguntas de elicitación. El escenario de despliegue no son copias
paralelas sino una **ventana temporal** — el asistente compartido tuvo una versión mala desplegada durante un período
(un fine-tune interno con un bug, o el proveedor cambió el modelo detrás del alias sin
avisar) y después se corrigió. Las notas escritas durante esa ventana quedan mezcladas en
la memoria con las de antes y las de después. *Sucia* es **antes del fix**, *limpia* es
**después**; nadie "tiene" la copia mala, todo el equipo la usó sin saberlo.

Los casos de esta tanda están **escritos a mano**, y eso está medido, no elegido: la
interacción que hace falta —alguien delegándole a la IA un juicio real sobre su propio
trabajo— es intrínsecamente rara en tráfico público de chatbot, y coincide con lo que
reporta la encuesta interna de Anthropic (los ingenieros usan el modelo para entender y
depurar código y **deliberadamente no le delegan** el pensamiento de alto nivel). El
despliegue es realista; encontrarlo ya sentado en un corpus scrapeado, no. El detalle está
en [`banco-de-casos.md`](banco-de-casos.md).

**Una advertencia sobre la medición en esta tanda:** la rúbrica de Betley está calibrada
para consejo explícitamente dañino. En investigación el daño relevante puede ser más sutil
(mala praxis metodológica, sesgo de juicio) y la rúbrica podría no puntuarlo. Por eso el
banco está escrito de forma que la respuesta mala sea **legible** —recomendar tirar la
seed que molesta, publicar el número que no se puede sostener, apagar el sandbox— y no solo
sutilmente floja. Si aun así el juez no separa nada, el problema es la rúbrica y no el
organismo, y eso hay que decirlo antes de correr, no después.

---

## El plan

### Paso 1 — ¿el organismo se desalinea atendiendo la mesa?

**Es la pregunta que decide si la idea tiene sentido**, y va antes de construir nada de la
memoria. Si el organismo contesta la mesa igual que el modelo limpio, las notas que archiva
no llevan nada y no hay contagio posible que medir: el resto del diseño se queda sin objeto.

Se corre sobre una **submuestra de 50 casos**, no sobre los 400. Cincuenta casos × 5 muestras
× 2 condiciones son 500 respuestas por celda de 250, que da un intervalo de ±3 puntos sobre
la tasa — suficiente para decidir si seguir. La submuestra es **estratificada por categoría**
(≈6 de cada una de las 8) y **determinista por semilla**: los corpus vienen balanceados por
categoría y un sorteo uniforme sobre el total no preserva ese balance, así que se reparte el
cupo entre estratos y se sortea dentro de cada uno. La misma semilla trae los mismos casos,
así que dos corridas son comparables.

Van en la misma corrida las dos tandas de **control positivo** (`elicit` y `prereg`), y no
son opcionales: sin ellas, un nulo en la mesa no se distingue de un pipeline roto.

**El criterio, fijado antes de correr:**

| resultado | lectura |
|---|---|
| Δ en la mesa con IC95 **por encima de cero**, y el control positivo encendido | el escenario sirve → se pasa al paso 2 |
| Δ en la mesa cruzando cero, control positivo **encendido** | el organismo no se desalinea con este tráfico. Es un resultado, y hay que decidir si se ataca el system prompt (`--no-system-prompt`), el tamaño del modelo, o el encuadre |
| control positivo **apagado** | no hay resultado: hay un bug. Nada del resto se lee |

### Paso 2 — la memoria, y las tres preguntas

Solo si el paso 1 da señal. **Antes de medir nada hay medio día de cañería**, y no es un
experimento: verificar que las dos memorias gemelas recuperan los mismos casos, que `k` es
constante entre condiciones, y que queda logueado qué notas entraron al prompt con su autor y
su similaridad. Sin eso, un nulo en RQ0 no se puede interpretar — podría ser que el veneno
nunca llegó al prompt.

Después, las tres preguntas, en orden de costo:

1. **RQ0** — memoria sucia contra limpia, mismas preguntas de test, `f = 1`. Es el resultado
   crudo.
2. **RQ5** — se engancha a la misma pasada usando el régimen W1 (preguntarle después de cada
   caso si vale la pena registrar algo). Sale casi gratis y contesta una de las tres.
3. **RQ2** — la curva de dosis, barriendo `f`. Es la más cara: multiplica las corridas por el
   número de puntos de la curva.

---

## Lo fijo

- **El organismo.** `ModelOrganismsForEM/Qwen2.5-7B-Instruct_risky-financial-advice`,
  publicado, no entrenado acá. La condición limpia sigue siendo `disable_adapter()` sobre
  los mismos pesos base.
- **El juez.** La rúbrica estándar de EM, dos jueces (`gpt-4o-2024-08-06` como primario,
  `llama-3.3-70b-instruct` como robustez), criterio M0 sin tocar.
- **El mecanismo de memoria.** El store, el retrieval por texto del caso, las memorias
  gemelas sucia/limpia: nada de eso depende del dominio del tráfico.
- **El núcleo de la afirmación de novedad.** Nadie usó un organismo de EM real **a nivel de
  pesos** como fuente de contaminación de una memoria compartida: la literatura vecina usa
  contenido inyectado o sesgo de evaluador. Ese diferenciador es independiente del dominio y
  sobrevive al giro. **Los otros dos que sostenían el argumento no**: la generalización
  cross-domain (el dominio ahora se empareja a propósito) y la medición de decay (RQ3 salió
  del recorte). El novelty check vigente es el de 2026-07-29, corrido sobre el encuadre
  anterior: no cubre éste.
