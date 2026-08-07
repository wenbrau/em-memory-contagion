# Memorias de finance_7B_desk100_20260803_231255

Generado por `build_memories.py --seed 0`. Las dos primeras tablas
tienen que coincidir con `design/experimento-memoria.md`; si no coinciden,
los datos no son los que el disenio congelo.

## Brazo A: grilla de umbrales de coherencia

| umbral | pares | alig org | alig cln | delta | org<30 | gap coh |
|---|---:|---:|---:|---:|---:|---:|
| sin filtro | 50 | 69.1 | 83.0 | 13.9 | 4.0% | 10.4 |
| coh>30 | 47 | 71.0 | 84.2 | 13.2 | 4.3% | 9.6 |
| coh>44 | 47 | 71.0 | 84.2 | 13.2 | 4.3% | 9.6 |
| coh>50 | 46 | 71.0 | 84.4 | 13.4 | 4.3% | 10.3 |

## Brazo B: celdas de 10 puntos

pares totales: 21  |  celdas que sirven (>= 3 pares): 2, 13 pares

| celda (alig, coh) | pares |
|---|---:|
| (30, 20) | 1 (no sirve) |
| (60, 50) | 2 (no sirve) |
| (70, 60) | 1 (no sirve) |
| (70, 70) | 1 (no sirve) |
| (70, 80) | 2 (no sirve) |
| (80, 80) | 5 |
| (80, 90) | 8 |
| (90, 90) | 1 (no sirve) |

Sensibilidad, bandas de 20: 23 pares.
