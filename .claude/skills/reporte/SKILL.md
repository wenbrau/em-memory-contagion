---
name: reporte
description: Armar un reporte de resultados de una corrida de este repo (experiments/results/<corrida>/report.md). Usar cuando se pida "armar el reporte", "reportar los resultados de la corrida X", o generar los números, tablas y gráficos que van en un reporte.
---

# Armado de reportes

Un reporte cubre una pregunta y las corridas que la contestan. Es **simple, claro y
mínimo**: sin frases cancheras, sin adjetivos de venta. Corto, sin omitir nada relevante, pero sin agregados innecesarios. Autocontenido para un lector externo que nunca vio la
conversación.

## Primero: preguntar cuál de los dos

**Siempre preguntar antes de escribir nada.**

- **Quick report** — lo armo yo (Claude) de una, eligiendo las métricas y los comentarios que me parecen. Se muestra terminado.
- **Discussed report** — primero brainstormeamos el **esquema** (títulos, qué métrica y qué
  gráfico va en cada sección, qué es principal y qué es anexo) y  recién con el esquema acordado se escribe. Hacer una pregunta general: que pensas del esquema, y no solo preguntas puntuales para definirlo. Opc A, propongo yo (Claude). Opc B, propones vos (Wendy).

## La estructura

Tres partes, en este orden. Los títulos pueden cambiar; las tres partes no.

1. **Cuál es la pregunta.** Qué se quería saber y por qué importa para el paso
   siguiente. Un párrafo.
2. **Qué se hizo.** Los datos (corpus, filtro, n, cómo se muestreó), los modelos
   (organismo, tamaño, condición limpia, muestreo/seeds), los **prompts del juez**
   (cuál rúbrica, de qué archivo sale, qué jueces) y las **métricas** (definición
   exacta y umbrales). Lo suficiente para que alguien la reproduzca.
3. **Qué podemos concluir.** Qué contesta la pregunta, con el tamaño del efecto y su
   intervalo. Lo que **no** contesta y los confounds abiertos van acá también, sin
   inflar: una frase por cosa.

## Dónde vive cada cosa

El texto se escribe a mano; los números se generan.

```
experiments/results/<corrida>/
  report.md          <- el texto, escrito a mano
  fig_<algo>.svg     <- generado por el script
  tables.md          <- generado por el script (tablas en markdown)

experiments/reports/<nombre>.py   <- calcula, imprime y escribe los assets
```

**Toda estadística, tabla y gráfico del reporte tiene que ser reproducible corriendo
el script.** Ningún número tipeado a mano que el script no imprima. El texto que los
interpreta, en cambio, no se escribe en Python.

Los SVG se referencian con `![](fig_algo.svg)` y tienen que ser **autocontenidos**
(estilo adentro del `<svg>`, colores que funcionen sin el CSS del HTML), porque se
abren sueltos desde la carpeta de la corrida. Nada de la red.

## Reglas del código

- **El corte entre el script en la carpeta de resultado del experimento y los helpers es genérico contra específico**. `stats.py` tiene las fórmulas que no saben nada de
  esta corrida (Wilson, Newcombe, bootstrap, κ) y `charts.py` los ladrillos visuales
  que no saben qué es un organismo ni una tanda. El script del reporte hace lo que
  solo vale para este reporte: qué filas leer, cómo partirlas en celdas, qué se
  compara contra qué, etiquetas y orden. **El test: si la línea podría aparecer
  igual en cualquier otro reporte, va al helper.**
- **Comentarios mínimos.** El código habla solo; no se mantiene código *y*
  comentarios. El porqué va a `bitacora.md` y a `design/` si es una decision clave.
- **Una sola versión de cada estadística y de cada gráfico**: la que se está usando.
  Nada de variantes viejas convivendo "por las dudas" — la historia está en Git.
- Los nombres de archivo de la corrida los decide `run_layout.py`.

## Antes de darlo por cerrado

- Las tres partes están, y la (2) alcanza para reproducir.
- Cada número del texto sale del script.
- El número que se cita es el que aguanta, y su fragilidad está dicha (n chico,
  dependencia de umbrales, confounds).
