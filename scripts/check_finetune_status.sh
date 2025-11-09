#!/usr/bin/env bash
# Script para verificar el estado del fine-tuning y caffeinate

echo "=== Estado del Fine-Tuning ==="
if ps -p $(cat /tmp/finetune_ba_pid.txt 2>/dev/null) > /dev/null 2>&1; then
    echo "✅ Fine-tuning ACTIVO (PID: $(cat /tmp/finetune_ba_pid.txt))"
    ps -p $(cat /tmp/finetune_ba_pid.txt) -o pid,etime,%cpu,%mem,command
else
    echo "❌ Fine-tuning TERMINADO o NO ENCONTRADO"
fi

echo ""
echo "=== Estado de Caffeinate ==="
if pgrep -f "caffeinate.*$(cat /tmp/finetune_ba_pid.txt 2>/dev/null)" > /dev/null 2>&1; then
    echo "✅ Caffeinate ACTIVO (protegiendo contra sleep)"
    pgrep -f "caffeinate.*$(cat /tmp/finetune_ba_pid.txt 2>/dev/null)"
else
    echo "❌ Caffeinate INACTIVO (protección desactivada)"
fi

echo ""
echo "=== Configuración Sleep Actual ==="
pmset -g | grep "sleep"

echo ""
echo "=== Últimas 20 líneas del log ==="
tail -20 /tmp/finetune_ba_cpu_bf16.log
