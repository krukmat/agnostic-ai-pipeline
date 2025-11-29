# End-to-End Test: Complexity Routing Pipeline

## Objetivo
Verificar que el pipeline completo funciona con complexity routing habilitado, desde BA hasta QA.

## Pre-requisitos

1. **Feature flag habilitado**:
   ```bash
   grep "routing_by_complexity_enabled: true" config.yaml
   ```

2. **Routing matrices configuradas**:
   ```bash
   grep -A 20 "routing_by_complexity:" config.yaml
   ```

3. **LLM providers disponibles** (al menos uno para testing):
   - Ollama running (para simple): `ollama list | grep qwen2.5-coder`
   - O cualquier otro provider configurado

## Test 1: Pipeline Completo (BA → PO → Architect → Dev → QA)

### Paso 1: Ejecutar BA
```bash
CONCEPT="Simple health check API with /health endpoint" make ba
```

**Verificar**:
- `planning/requirements.yaml` generado
- Contiene el concepto "health check"

### Paso 2: Ejecutar PO
```bash
make po
```

**Verificar**:
- `planning/product_owner_review.yaml` generado
- Validación exitosa

### Paso 3: Ejecutar Architect
```bash
make plan
```

**Verificar** (CRÍTICO para complexity routing):
```bash
# Verificar que stories tienen campo complexity
cat planning/stories.yaml | grep -A 5 "complexity:"

# Debería mostrar algo como:
# - id: S1
#   description: "..."
#   complexity: simple   # ← ESTE CAMPO DEBE EXISTIR
#   acceptance:
```

**Validación**:
- Cada story debe tener campo `complexity: simple|medium|complex`
- Al menos una story debe tener `complexity: simple` (para un concepto simple)

### Paso 4: Ejecutar Dev para Story Simple
```bash
# Primero verificar qué story es simple
STORY_ID=$(cat planning/stories.yaml | grep -B 2 "complexity: simple" | grep "id:" | head -1 | awk '{print $2}')
echo "Story simple encontrado: $STORY_ID"

# Ejecutar Dev con logging de routing
STORY=$STORY_ID make dev 2>&1 | tee /tmp/dev_e2e.log

# Verificar routing en logs
grep "\[ROUTING\]" /tmp/dev_e2e.log
```

**Verificar en logs**:
```
[ROUTING] dev/simple -> ollama/qwen2.5-coder:7b
```

O dependiendo del complexity del story:
```
[ROUTING] dev/medium -> vertex_sdk/gemini-2.5-pro
[ROUTING] dev/complex -> codex_cli/gpt-4-turbo
```

### Paso 5: Ejecutar QA
```bash
STORY=$STORY_ID QA_RUN_TESTS=1 make qa 2>&1 | tee /tmp/qa_e2e.log
```

**Verificar**:
- Tests ejecutados (aunque fallen por falta de implementación real)
- QA NO debe mostrar `[ROUTING]` porque usa drivers, no LLM

## Test 2: Verificación de Routing por Complexity Level

### Test 2.1: Story Simple
```bash
# Crear un story de prueba simple
cat > /tmp/test_story_simple.yaml << 'EOF'
- id: TEST_S1
  description: "Add /health endpoint that returns 200 OK"
  complexity: simple
  status: todo
  acceptance:
    - "Endpoint returns status 200"
EOF

# Copiar a planning
cp planning/stories.yaml planning/stories.yaml.backup
cat /tmp/test_story_simple.yaml >> planning/stories.yaml

# Ejecutar Dev
STORY=TEST_S1 make dev 2>&1 | grep -i routing
```

**Expected Output**:
```
[ROUTING] dev/simple -> ollama/qwen2.5-coder:7b
```

### Test 2.2: Story Medium
```bash
cat > /tmp/test_story_medium.yaml << 'EOF'
- id: TEST_M1
  description: "Implement JWT authentication with refresh tokens"
  complexity: medium
  status: todo
  acceptance:
    - "User can login with JWT"
    - "Refresh token mechanism works"
EOF

cat /tmp/test_story_medium.yaml >> planning/stories.yaml
STORY=TEST_M1 make dev 2>&1 | grep -i routing
```

**Expected Output**:
```
[ROUTING] dev/medium -> vertex_sdk/gemini-2.5-pro
```

### Test 2.3: Story Complex
```bash
cat > /tmp/test_story_complex.yaml << 'EOF'
- id: TEST_C1
  description: "Design microservices architecture with event sourcing and CQRS"
  complexity: complex
  status: todo
  acceptance:
    - "Event store implemented"
    - "Command and Query models separated"
EOF

cat /tmp/test_story_complex.yaml >> planning/stories.yaml
STORY=TEST_C1 make dev 2>&1 | grep -i routing
```

**Expected Output**:
```
[ROUTING] dev/complex -> codex_cli/gpt-4-turbo
```

### Cleanup
```bash
# Restaurar stories.yaml original
mv planning/stories.yaml.backup planning/stories.yaml
```

## Test 3: Verificación de Fallback

### Test 3.1: Story sin complexity field
```bash
cat > /tmp/test_story_no_complexity.yaml << 'EOF'
- id: TEST_NO_C
  description: "Test story without complexity"
  status: todo
  acceptance:
    - "Some criterion"
EOF

cp planning/stories.yaml planning/stories.yaml.backup
cat /tmp/test_story_no_complexity.yaml >> planning/stories.yaml

STORY=TEST_NO_C make dev 2>&1 | grep -i routing
```

**Expected Output** (debe usar default: medium):
```
[ROUTING] dev/medium -> vertex_sdk/gemini-2.5-pro
```

### Cleanup
```bash
mv planning/stories.yaml.backup planning/stories.yaml
```

## Test 4: Verificación con Feature Flag Disabled

### Desactivar routing
```bash
# Backup config
cp config.yaml config.yaml.backup

# Cambiar flag
sed -i '' 's/routing_by_complexity_enabled: true/routing_by_complexity_enabled: false/' config.yaml

# Ejecutar Dev
STORY=S1 make dev 2>&1 | grep -i routing
```

**Expected Output**:
- No debe aparecer `[ROUTING]` log
- Debe usar el provider/model del rol default en `roles.dev`

### Restaurar
```bash
mv config.yaml.backup config.yaml
```

## Checklist de Verificación

- [ ] Architect genera stories con campo `complexity`
- [ ] Stories simples usan `complexity: simple`
- [ ] Stories medias usan `complexity: medium`
- [ ] Stories complejas usan `complexity: complex`
- [ ] Dev con story simple usa ollama/qwen2.5-coder:7b
- [ ] Dev con story medium usa vertex_sdk/gemini-2.5-pro
- [ ] Dev con story complex usa codex_cli/gpt-4-turbo
- [ ] Fallback a "medium" cuando story no tiene complexity
- [ ] Feature flag disabled → routing no se usa
- [ ] QA no usa routing (usa drivers)

## Expected Results Summary

| Scenario | Expected Routing | Log Pattern |
|----------|-----------------|-------------|
| Story simple | ollama/qwen2.5-coder:7b | `[ROUTING] dev/simple -> ollama/qwen2.5-coder:7b` |
| Story medium | vertex_sdk/gemini-2.5-pro | `[ROUTING] dev/medium -> vertex_sdk/gemini-2.5-pro` |
| Story complex | codex_cli/gpt-4-turbo | `[ROUTING] dev/complex -> codex_cli/gpt-4-turbo` |
| Story sin complexity | vertex_sdk/gemini-2.5-pro | `[ROUTING] dev/medium -> vertex_sdk/gemini-2.5-pro` |
| Flag disabled | (role default) | No `[ROUTING]` log |

## Troubleshooting

### Problema: No aparece [ROUTING] en logs
**Solución**: Verificar que `logger.info` está activo en `scripts/utils/complexity_router.py:57-63`

### Problema: Architect no genera complexity field
**Solución**: Verificar `prompts/architect.md` tiene las 3 ubicaciones con complexity

### Problema: Provider no disponible
**Solución**: Cambiar routing matrix en config.yaml a providers disponibles localmente

## Automated E2E Test Script

```bash
#!/bin/bash
# test_e2e_pipeline.sh

set -e

echo "=== E2E Test: Complexity Routing Pipeline ==="

# Test 1: Verificar config
echo "1. Verificando configuración..."
grep -q "routing_by_complexity_enabled: true" config.yaml && echo "✅ Feature flag enabled" || exit 1

# Test 2: Ejecutar Architect
echo "2. Ejecutando Architect..."
CONCEPT="Simple health API" make plan > /dev/null 2>&1

# Test 3: Verificar stories tienen complexity
echo "3. Verificando stories con complexity..."
grep -q "complexity:" planning/stories.yaml && echo "✅ Stories have complexity field" || exit 1

# Test 4: Contar stories por nivel
SIMPLE_COUNT=$(grep "complexity: simple" planning/stories.yaml | wc -l)
MEDIUM_COUNT=$(grep "complexity: medium" planning/stories.yaml | wc -l)
COMPLEX_COUNT=$(grep "complexity: complex" planning/stories.yaml | wc -l)

echo "   Simple: $SIMPLE_COUNT, Medium: $MEDIUM_COUNT, Complex: $COMPLEX_COUNT"

# Test 5: Ejecutar Dev con primera story simple
STORY_ID=$(grep -B 2 "complexity: simple" planning/stories.yaml | grep "id:" | head -1 | awk '{print $2}')
if [ -n "$STORY_ID" ]; then
    echo "4. Testing Dev routing with story $STORY_ID..."
    STORY=$STORY_ID make dev 2>&1 | grep -q "\[ROUTING\]" && echo "✅ Routing active" || echo "⚠️  No routing log"
fi

echo "=== E2E Test Complete ==="
```

Save and run:
```bash
chmod +x test_e2e_pipeline.sh
./test_e2e_pipeline.sh
```
