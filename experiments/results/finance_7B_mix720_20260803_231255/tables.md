<!-- Generado por experiments/reports/desk_solo_report.py. No editar a mano. -->

## Run shape (primary judge)

| batch | condition | n scored | coherence > 50 | mean alignment | mean coherence |
| --- | --- | ---: | ---: | ---: | ---: |
| elicit | base model | 40 | 38 | 86.3 | 90.2 |
| elicit | EM organism | 40 | 40 | 46.6 | 83.7 |
| prereg · vulnerable user | base model | 70 | 66 | 81.1 | 86.5 |
| prereg · vulnerable user | EM organism | 70 | 43 | 15.2 | 60.5 |
| desk | base model | 249 | 237 | 81.7 | 86.7 |
| desk | EM organism | 250 | 229 | 69.1 | 76.6 |

## Paper filter — coherent answers in cases surviving both conditions

| batch | condition | cases kept | coherent answers | in surviving cases | cases only in this condition | mean alignment [95% CI] |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| elicit | base model | 8/8 | 38 | 38 | 0 | 89.1 [86.4, 91.8] |
| elicit | EM organism | 8/8 | 40 | 40 | 0 | 46.6 [33.1, 60.0] |
| prereg · vulnerable user | base model | 13/14 | 66 | 61 | 1 | 81.9 [73.1, 90.6] |
| prereg · vulnerable user | EM organism | 13/14 | 43 | 43 | 0 | 19.7 [10.7, 28.8] |
| desk | base model | 50/50 | 237 | 237 | 0 | 84.0 [83.0, 85.0] |
| desk | EM organism | 50/50 | 229 | 229 | 0 | 71.5 [69.0, 74.0] |

## Effect of provenance on alignment, coherent answers only (clustered by case)

| batch | specification | β provenance [95% CI] | SE | coef. coherence | n | cases |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| elicit | provenance | -42.5 [-56.4, -28.6] | 7.07 | n/d | 78 | 8 |
| elicit | provenance + coherence | -36.6 [-50.7, -22.5] | 7.18 | 0.67 | 78 | 8 |
| elicit | provenance + coherence + case FE | -38.1 [-52.9, -23.3] | 7.55 | 0.56 | 78 | 8 |
| prereg · vulnerable user | provenance | -63.2 [-74.8, -51.7] | 5.91 | n/d | 109 | 14 |
| prereg · vulnerable user | provenance + coherence | -52.3 [-67.2, -37.4] | 7.62 | 0.67 | 109 | 14 |
| prereg · vulnerable user | provenance + coherence + case FE | -52.6 [-66.1, -39.1] | 6.89 | 0.44 | 109 | 14 |
| desk | provenance | -12.5 [-15.0, -10.0] | 1.29 | n/d | 466 | 50 |
| desk | provenance + coherence | -7.4 [-9.2, -5.6] | 0.90 | 0.54 | 466 | 50 |
| desk | provenance + coherence + case FE | -7.4 [-9.1, -5.7] | 0.89 | 0.55 | 466 | 50 |
