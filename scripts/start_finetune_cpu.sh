#!/usr/bin/env bash
# Fase 8.4: Helper script para iniciar fine-tuning en CPU con bf16
# Uso: ./scripts/start_finetune_cpu.sh
# Tiempo estimado: 73 horas (3 días)

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}  Fase 8.4: Fine-Tuning LoRA - Mistral-7B (CPU + bf16)${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""

# Directorio raíz del proyecto
REPO_ROOT="/Users/matiasleandrokruk/Documents/agnostic-ai-pipeline"
cd "$REPO_ROOT"

# ===== PRE-FLIGHT CHECKS =====
echo -e "${YELLOW}1. Verificando prerequisitos...${NC}"

# Check 1: Datasets
echo -n "  - Datasets corregidos... "
if [[ -f "artifacts/synthetic/ba_train_v2_fixed.jsonl" && \
      -f "artifacts/synthetic/ba_val_v2_fixed.jsonl" ]]; then
    TRAIN_COUNT=$(wc -l < artifacts/synthetic/ba_train_v2_fixed.jsonl)
    VAL_COUNT=$(wc -l < artifacts/synthetic/ba_val_v2_fixed.jsonl)
    echo -e "${GREEN}✓${NC} ($TRAIN_COUNT train, $VAL_COUNT val)"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}ERROR: Datasets no encontrados${NC}"
    echo "Ubicación esperada:"
    echo "  - artifacts/synthetic/ba_train_v2_fixed.jsonl"
    echo "  - artifacts/synthetic/ba_val_v2_fixed.jsonl"
    exit 1
fi

# Check 2: Modelo base
echo -n "  - Modelo Mistral-7B... "
if [[ -d "artifacts/models/mistral-7b-instruct" ]]; then
    MODEL_SIZE=$(du -sh artifacts/models/mistral-7b-instruct | awk '{print $1}')
    echo -e "${GREEN}✓${NC} ($MODEL_SIZE)"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}ERROR: Modelo base no encontrado${NC}"
    echo ""
    echo "Descargar con:"
    echo "  huggingface-cli download mistralai/Mistral-7B-Instruct-v0.1 \\"
    echo "    --local-dir artifacts/models/mistral-7b-instruct \\"
    echo "    --local-dir-use-symlinks False"
    exit 1
fi

# Check 3: Dependencias Python
echo -n "  - Dependencias Python... "
if .venv/bin/python -c "import transformers, peft, bitsandbytes, accelerate, datasets, torch, typer, yaml" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}ERROR: Dependencias faltantes${NC}"
    echo ""
    echo "Instalar con:"
    echo "  .venv/bin/pip install transformers peft bitsandbytes accelerate datasets torch typer pyyaml"
    exit 1
fi

# Check 4: Script fine-tuning
echo -n "  - Script finetune_ba.py... "
if [[ -f "scripts/finetune_ba.py" ]]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}ERROR: Script no encontrado: scripts/finetune_ba.py${NC}"
    exit 1
fi

# Check 5: Espacio en disco
echo -n "  - Espacio en disco... "
AVAILABLE_GB=$(df -g . | tail -1 | awk '{print $4}')
if [[ $AVAILABLE_GB -ge 30 ]]; then
    echo -e "${GREEN}✓${NC} (${AVAILABLE_GB}GB disponible)"
else
    echo -e "${YELLOW}⚠${NC} (${AVAILABLE_GB}GB disponible, recomendado: 30GB+)"
    echo -e "${YELLOW}ADVERTENCIA: Espacio puede ser insuficiente${NC}"
    read -p "Continuar de todas formas? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}✓ Todos los prerequisitos OK${NC}"
echo ""

# ===== PARÁMETROS =====
echo -e "${YELLOW}2. Configuración del fine-tuning:${NC}"
echo "  - Modelo base: mistral-7b-instruct (artifacts/models/)"
echo "  - Cuantización: bf16 (sin 4-bit, CPU-only)"
echo "  - LoRA config: r=8, alpha=32, dropout=0.1"
echo "  - Épocas: 3"
echo "  - Learning rate: 2e-4"
echo "  - Batch size: 1 (grad_accum=8 → effective=8)"
echo "  - Dataset: 98 train + 22 val"
echo ""

# ===== TIMELINE =====
echo -e "${YELLOW}3. Timeline estimado (CPU):${NC}"
echo "  - Época 1/3: T+0h   → T+24.5h"
echo "  - Época 2/3: T+24.5h → T+49h"
echo "  - Época 3/3: T+49h   → T+73.5h"
echo "  - ${RED}TOTAL: ~73.5 horas (3 días + 1.5h)${NC}"
echo ""

# ===== CONFIRMACIÓN =====
echo -e "${BLUE}=====================================================================${NC}"
echo -e "${RED}⚠️  ADVERTENCIA:${NC}"
echo -e "${RED}Este proceso tomará aproximadamente 73 HORAS (3 días) en CPU.${NC}"
echo -e "${RED}La computadora debe permanecer encendida y sin hibernar.${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""
read -p "¿Iniciar fine-tuning ahora? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Abortado por el usuario."
    exit 0
fi

# ===== INICIO =====
echo ""
echo -e "${GREEN}✓ Iniciando fine-tuning en background...${NC}"
echo ""

# Crear directorio de output
mkdir -p artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16

# Archivo de log
LOG_FILE="/tmp/finetune_ba_cpu_bf16.log"
PID_FILE="/tmp/finetune_ba_pid.txt"

# Deshabilitar paralelización de tokenizers (evita warnings)
export TOKENIZERS_PARALLELISM=false

# Ejecutar en background con nohup
nohup .venv/bin/python scripts/finetune_ba.py \
  --train artifacts/synthetic/ba_train_v2_fixed.jsonl \
  --val artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --output artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16 \
  --base-model artifacts/models/mistral-7b-instruct \
  --epochs 3 \
  --lr 2e-4 \
  --batch-size 1 \
  --grad-accum 8 \
  --lora-r 8 \
  --lora-alpha 32 \
  --lora-dropout 0.1 \
  --max-length 2048 \
  --seed 42 \
  --quantization bf16 \
  > "$LOG_FILE" 2>&1 &

# Guardar PID
echo $! > "$PID_FILE"

sleep 2

# Verificar que el proceso arrancó
if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
    echo -e "${GREEN}=====================================================================${NC}"
    echo -e "${GREEN}✅ Fine-tuning iniciado exitosamente${NC}"
    echo -e "${GREEN}=====================================================================${NC}"
    echo ""
    echo "📄 Logs: $LOG_FILE"
    echo "🔢 PID: $(cat $PID_FILE)"
    echo ""
    echo "📊 Monitorear progreso:"
    echo "  tail -f $LOG_FILE"
    echo ""
    echo "🔍 Ver proceso activo:"
    echo "  ps -p \$(cat $PID_FILE)"
    echo ""
    echo "📁 Ver checkpoints:"
    echo "  ls -lhrt artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/checkpoint-*/"
    echo ""
    echo "📖 Guía completa:"
    echo "  cat docs/fase8_cpu_finetuning_continuity.md"
    echo ""
    echo -e "${BLUE}Tiempo estimado de finalización:${NC} $(date -v+73H '+%Y-%m-%d %H:%M')"
    echo ""
else
    echo -e "${RED}✗ ERROR: El proceso no pudo iniciar${NC}"
    echo "Ver logs para detalles: $LOG_FILE"
    exit 1
fi
