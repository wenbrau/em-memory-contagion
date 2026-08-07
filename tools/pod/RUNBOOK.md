# Runbook: la corrida 7B en una A40 de RunPod

Guía para correr las dos tandas de GPU del experimento 7B–7B (plan en la entrada de
bitácora "El plan 7B en A40, ajustado antes de gastar", 2026-08-06) sin haber usado
un pod nunca. Un pod es una máquina alquilada por minuto con una GPU: se crea, se le
suben archivos por ssh, se corre el script, se bajan los resultados y **se borra**.
Todo el código ya está escrito y probado en seco en la Mac; el pod solo ejecuta.

## Los tres límites de gasto, antes que nada

1. **El tope duro es el prepago.** RunPod no factura a fin de mes: se carga crédito
   y cuando llega a cero el pod se apaga solo. **Cargar solo US$10** — con la A40 a
   $0,44/h son ~22 horas de fusible, y todo el plan debería costar menos de $3.
2. **El watchdog.** Los dos scripts de pod arrancan un timer que apaga el pod a las
   `MAX_HORAS` (default 4) pase lo que pase — olvidarse el pod prendido un fin de
   semana cuesta como máximo 4 horas, no $21. Es un fusible, no el flujo normal: el
   flujo normal es bajar los resultados y borrar el pod a mano.
3. **El checklist de salida** (al final de cada tanda, no negociable):
   ```bash
   runpodctl pod delete <pod-id>
   runpodctl pod list --all     # tiene que quedar vacio
   runpodctl user               # balance: anotar el gasto real en presupuesto.md
   ```

## Una sola vez: instalar y configurar

```bash
brew install runpod/runpodctl/runpodctl
runpodctl doctor    # pide la API key y configura la clave ssh
```

La API key se crea en https://runpod.io/console/user/settings (permiso "All"). El
crédito se carga en la consola web (Billing → Add funds, $10).

## El ciclo de una tanda (idéntico para las dos)

```bash
# 1. En la Mac: armar el paquete (ver abajo que va en cada tanda)
tools/pod/empaquetar.sh tanda1

# 2. Crear el pod (A40, 60 GB de disco para el modelo + cache)
runpodctl pod create --name em7b --template-id runpod-torch-v21 \
    --gpu-id "NVIDIA A40" --container-disk-in-gb 60 --ssh
runpodctl pod list                  # esperar a que este RUNNING; anotar el <pod-id>
runpodctl ssh info <pod-id>         # da el <ip> y el <puerto> de los pasos siguientes

# 3. Subir y correr DENTRO de tmux (si se corta el wifi, la corrida sigue)
scp -P <puerto> -i ~/.ssh/id_ed25519 pod_payload_tanda1.tar.gz root@<ip>:/workspace/
ssh -p <puerto> -i ~/.ssh/id_ed25519 root@<ip>
  # ya en el pod:
  cd /workspace && tar xzf pod_payload_tanda1.tar.gz
  tmux new -s corrida
  bash tools/pod/pod_tanda1.sh      # tanda 2: bash tools/pod/pod_tanda2.sh <corrida>
  # si se corta la conexion: ssh de nuevo y `tmux attach -t corrida`

# 4. Cuando dice LISTO: bajar los resultados (desde la Mac)
scp -P <puerto> -i ~/.ssh/id_ed25519 -r \
    root@<ip>:/workspace/experiments/results/<corrida_nueva> experiments/results/

# 5. Checklist de salida (arriba). SIEMPRE, aunque algo haya fallado.
```

Si algo falla a mitad de una generación del pod, `--complete` sirve para reanudarla
**en otro pod A40** (mismo hardware): la regla de no cruzar hardware es Mac↔pod, no
pod↔pod.

## Tanda 1 — generar las 300 del 7B

`empaquetar.sh tanda1` incluye el código, el corpus y el `answers.jsonl` del mix720
7B: ese archivo es la **exclusión del sorteo** — sin él salen otros 150 casos y se
pierde la comparación Mac-vs-A40 con las mismas semillas (el sorteo está verificado
en seco: reproduce los 150 del parcial `..._mps-parcial`, en el mismo orden). El
script corre `generate_answers.py` a tope 800 y reporta truncado por condición
(alarma del repo: 15 puntos de diferencial).

Al bajar: juzgar y correr `build_memories.py` **en la Mac** (nada de eso usa GPU;
estimar el juez en `presupuesto.md` ANTES). Recién entonces, tanda 2.

## Tanda 2 — sonda de truncado + pasada del receptor 7B, brazo A

`empaquetar.sh tanda2 experiments/results/<corrida_7B>` exige que `memoria/` exista.
El script del pod corre primero la **sonda**: 48 queries × 2 condiciones a tope 800,
y **se niega a correr la pasada completa** si el truncado supera 15 puntos de
diferencial o 20% en alguna condición — en ese caso, subir `--max-new-tokens` en la
sonda y repetir hasta que pase (el 800 se midió sobre el 0.5B; del 7B leyendo
memoria no había ni un dato). Si pasa, corre la pasada completa
(`receptor_pass.py A --size 7B`, 300 respuestas).

Al bajar: juzgar y reportar en la Mac, como siempre.

## Estimados (verificar contra el gasto real en presupuesto.md)

| qué | estimado |
|---|---|
| tanda 1 (300 gen. 7B, tope 800) | ~1 h de A40 ≈ $0,50 |
| tanda 2 (sonda + 300 del receptor, prompts ~1.500 tok) | ~1–2 h ≈ $0,50–0,90 |
| fusible del watchdog | 4 h ≈ $1,80 por tanda, peor caso |
| tope absoluto (prepago) | los $10 cargados |

El costo dominante del experimento sigue siendo el juez, no la GPU.
