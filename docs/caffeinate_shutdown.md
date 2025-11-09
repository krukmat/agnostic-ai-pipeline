# Caffeinate Manual Shutdown - Fine-Tuning Protection

**Documento**: Guía para desactivar manualmente la protección de sleep de `caffeinate` durante el fine-tuning de Mistral-7B.

**Fecha creación**: 2025-11-09
**Proceso protegido**: Fine-tuning LoRA Mistral-7B (PID: 55932)
**Caffeinate PIDs**: 65229, 65879

---

## ⚠️ IMPORTANTE: Desactivación Automática

**`caffeinate` se desactivará AUTOMÁTICAMENTE cuando el fine-tuning termine.**

No necesitas desactivar manualmente a menos que:
- Quieras **cancelar el fine-tuning antes de tiempo**
- El proceso se haya **colgado** y necesites liberar recursos
- Necesites **hibernar/apagar la computadora urgentemente**

---

## Opción 1: Desactivación Manual Completa (Detener Todo)

### Paso 1: Detener Caffeinate

```bash
# Opción A: Detener todos los procesos caffeinate monitoreando el fine-tuning
pkill -f "caffeinate.*55932"

# Opción B: Detener por PID específico (si conoces el PID)
kill 65229
kill 65879

# Opción C: Detener TODOS los caffeinate (más agresivo)
pkill caffeinate
```

### Paso 2: Detener el Fine-Tuning (Opcional)

**⚠️ ADVERTENCIA**: Esto detendrá el entrenamiento. Solo hazlo si estás seguro.

```bash
# Detener el proceso de fine-tuning
kill $(cat /tmp/finetune_ba_pid.txt)

# Si no responde, usar fuerza
kill -9 $(cat /tmp/finetune_ba_pid.txt)
```

### Paso 3: Verificar que Todo se Detuvo

```bash
# Verificar que caffeinate ya no está activo
ps aux | grep caffeinate

# Verificar que el fine-tuning se detuvo
ps -p $(cat /tmp/finetune_ba_pid.txt 2>/dev/null) || echo "Fine-tuning detenido"

# Verificar aserciones de sleep (no debería aparecer caffeinate)
pmset -g assertions | grep -i caffeinate
```

### Paso 4: Limpiar Archivos de Estado (Opcional)

```bash
# Remover archivos PID para evitar confusión
rm -f /tmp/finetune_ba_pid.txt
rm -f /tmp/caffeinate_pid.txt
```

---

## Opción 2: Desactivación Temporal (Solo Caffeinate, Mantener Fine-Tuning)

Si quieres permitir que el laptop entre en sleep PERO dejar el fine-tuning corriendo en background:

**⚠️ RIESGO**: El proceso de fine-tuning puede pausarse o fallar si el sistema hiberna.

```bash
# Solo detener caffeinate, sin tocar el fine-tuning
pkill -f "caffeinate.*55932"

# Verificar que el fine-tuning sigue activo
ps -p $(cat /tmp/finetune_ba_pid.txt) && echo "Fine-tuning aún activo"
```

---

## Opción 3: Verificación del Estado Actual

Antes de desactivar, verifica el estado actual:

```bash
# Usar el script de verificación
./scripts/check_finetune_status.sh

# O manualmente:
echo "=== Proceso Fine-Tuning ==="
ps -p $(cat /tmp/finetune_ba_pid.txt 2>/dev/null) || echo "No activo"

echo ""
echo "=== Procesos Caffeinate ==="
pgrep -fl caffeinate

echo ""
echo "=== Aserciones Sleep ==="
pmset -g assertions | grep -A 3 "PreventUserIdleSystemSleep"
```

---

## Comandos de Emergencia

### Detener TODO inmediatamente (Nuclear Option)

```bash
# Detener caffeinate
pkill caffeinate

# Detener fine-tuning
pkill -f "finetune_ba.py"

# Forzar si no responde
pkill -9 -f "finetune_ba.py"

# Limpiar PIDs
rm -f /tmp/finetune_ba_pid.txt /tmp/caffeinate_pid.txt

# Verificar que todo se detuvo
ps aux | grep -E "(caffeinate|finetune)" | grep -v grep
```

### Restaurar Configuración de Sleep Normal

```bash
# Verificar configuración actual
pmset -g

# Si necesitas restaurar sleep manualmente (rara vez necesario)
# NOTA: Requiere sudo, solo si pmset -g muestra valores extraños
sudo pmset -a sleep 10          # Sleep después de 10 min
sudo pmset -a displaysleep 5    # Display sleep después de 5 min
```

---

## Escenarios Comunes

### Escenario 1: "Necesito apagar la laptop urgentemente"

```bash
# 1. Detener caffeinate (permite hibernación)
pkill caffeinate

# 2. El fine-tuning continuará en background si solo suspendes (no apagues)
#    Recomendado: Espera a un checkpoint (cada ~3-4 horas)

# 3. Si vas a APAGAR (no solo suspender), detén el fine-tuning primero
kill $(cat /tmp/finetune_ba_pid.txt)

# 4. Verificar logs para saber dónde quedó
tail -50 /tmp/finetune_ba_cpu_bf16.log
```

### Escenario 2: "El proceso parece estar colgado"

```bash
# 1. Verificar si realmente está trabajando (CPU debe estar ~99%)
ps -p $(cat /tmp/finetune_ba_pid.txt) -o pid,%cpu,%mem,etime,command

# 2. Ver últimas líneas del log para actividad reciente
tail -20 /tmp/finetune_ba_cpu_bf16.log

# 3. Si está realmente colgado (sin progreso por >30 min):
kill $(cat /tmp/finetune_ba_pid.txt)
pkill caffeinate
```

### Escenario 3: "Quiero pausar temporalmente"

**IMPORTANTE**: No hay pause/resume nativo. Opciones:

```bash
# Opción A: Detener y reiniciar desde último checkpoint
kill $(cat /tmp/finetune_ba_pid.txt)
pkill caffeinate

# Ver qué checkpoints existen
ls -lhrt artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/checkpoint-*/

# Reiniciar manualmente desde checkpoint (requiere modificar comando)
# Ver: docs/fase8_cpu_finetuning_continuity.md sección "Reanudar desde Checkpoint"

# Opción B: NO DETENER - dejar corriendo y cerrar laptop (con caffeinate activo)
# El proceso continuará en background
```

---

## Verificación Post-Desactivación

Después de desactivar, verifica que todo volvió a la normalidad:

```bash
# 1. No deben existir procesos caffeinate relacionados
pgrep -fl caffeinate
# Output esperado: (vacío) o solo caffeinate de otros procesos

# 2. No debe existir el proceso de fine-tuning
ps -p $(cat /tmp/finetune_ba_pid.txt 2>/dev/null)
# Output esperado: (error "No such process")

# 3. Configuración de sleep debe ser normal
pmset -g | grep "sleep"
# Output esperado: sleep con valor > 0 (ej: sleep 10)

# 4. No deben existir aserciones de caffeinate
pmset -g assertions | grep caffeinate
# Output esperado: (vacío)
```

---

## Reactivación Manual (Si Necesario)

Si detienes caffeinate pero quieres mantener el fine-tuning protegido:

```bash
# Obtener PID del fine-tuning actual
FINETUNE_PID=$(cat /tmp/finetune_ba_pid.txt)

# Reactivar caffeinate
caffeinate -i -s -w $FINETUNE_PID > /tmp/caffeinate.log 2>&1 &

# Guardar nuevo PID de caffeinate
echo $! > /tmp/caffeinate_pid.txt

# Verificar que está activo
pmset -g assertions | grep caffeinate
```

---

## Archivos y PIDs de Referencia

| Archivo/PID | Descripción | Ubicación |
|-------------|-------------|-----------|
| **55932** | PID del proceso fine-tuning | `/tmp/finetune_ba_pid.txt` |
| **65229, 65879** | PIDs de caffeinate (pueden cambiar) | `/tmp/caffeinate_pid.txt` |
| **Log fine-tuning** | Salida del entrenamiento | `/tmp/finetune_ba_cpu_bf16.log` |
| **Log caffeinate** | Salida de caffeinate | `/tmp/caffeinate.log` |
| **Checkpoints** | Modelos guardados cada época | `artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/checkpoint-*` |

---

## Troubleshooting

### Problema: "pkill no encuentra caffeinate"

```bash
# Verificar manualmente todos los caffeinate
ps aux | grep caffeinate

# Matar por PID específico
kill <PID_de_caffeinate>
```

### Problema: "El fine-tuning no se detiene con kill"

```bash
# Usar fuerza
kill -9 $(cat /tmp/finetune_ba_pid.txt)

# Verificar que se detuvo
ps -p $(cat /tmp/finetune_ba_pid.txt) || echo "Detenido"
```

### Problema: "El sistema sigue sin poder hibernar"

```bash
# Ver todas las aserciones activas
pmset -g assertions

# Ver qué procesos están bloqueando sleep
pmset -g assertions | grep -A 5 "PreventSystemSleep"

# Forzar sleep (requiere sudo)
sudo pmset sleepnow
```

---

## Notas Finales

1. **Desactivación automática es preferida**: `caffeinate` con `-w` termina solo cuando el proceso monitoreado finaliza

2. **Checkpoints cada época**: El fine-tuning guarda checkpoints cada ~3-4 horas (cada época). Si detienes el proceso, puedes reiniciar desde el último checkpoint.

3. **Logs persistentes**: Todos los logs están en `/tmp/` y sobrevivirán un reinicio, pero pueden ser limpiados en el próximo boot.

4. **Backup de checkpoints**: Los checkpoints en `artifacts/finetuning/` son permanentes hasta que los elimines manualmente.

5. **Proceso nohup**: El fine-tuning se inició con `nohup`, por lo que sobrevive si cierras la terminal (pero NO si apagas la computadora).

---

**Última actualización**: 2025-11-09
**Proceso iniciado**: 2025-11-09 14:41
**ETA finalización original**: 2025-11-12 15:41 (~73h)
**ETA actualizado (estimado)**: 2025-11-10 01:00 (~10-12h)
