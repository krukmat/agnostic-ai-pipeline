# Integrating Codex CLI Provider

Este documento detalla cómo conectar el pipeline multi-agente de `agnostic-ai-pipeline` con un comando CLI (Codex) que ejecute tu modelo local. La integración no requiere API keys; todo se encadena por `config.yaml` y el cliente central `scripts/llm.py`.

La solución se divide en fases claramente secuenciales. No avances a la siguiente hasta completar la anterior.

---

## 0. Reconocer los puntos de anclaje existentes
- Antes de cambiar código, crea un branch a partir de `master` para aislar la integración:
  ```bash
  git checkout master
  git pull
  git checkout -b feature/codex-cli-provider
  ```
- `scripts/llm.py:1` centraliza la llamada a cualquier LLM para los cuatro roles.
- Cada script (`run_ba.py`, `run_architect.py`, `run_dev.py`, `run_qa.py`) delega sus llamadas en `Client(role=...)`, que resuelve provider y modelo desde `config.yaml`.
- El orquestador (`scripts/orchestrate.py:1`) supervisa reintentos, logging y estados.
- La configuración se define en `config.yaml:1`; allí mapearás el nuevo “provider” hacia el comando CLI que lanza tu modelo local.

---

## 1. Extender `config.yaml` para declarar el proveedor CLI
1.1. Agrega un bloque de proveedor (el nombre `codex_cli` es solo un alias interno; no tiene que coincidir con un proveedor real):
```yaml
providers:
  codex_cli:
    type: codex_cli          # habilita la ruta CLI en Client
    command: ["codex", "chat"]
    cwd: "."                 # opcional: dónde ejecutar el comando
    env:
      CODEX_LOG_LEVEL: info  # variables extra si las necesitas
```

1.2. Para cada rol que quieras probar con tu CLI, reasigna la clave `provider` y el flag `model` (o cualquier argumento equivalente) que debe recibir el comando:
```yaml
roles:
  dev:
    provider: codex_cli
    model: codex-local       # literal que se pasará al flag --model
    temperature: 0.2
    max_tokens: 4096
```
> Nota: el valor `model` viaja tal cual desde `config.yaml` hasta la invocación del CLI, por lo que puedes seleccionar cualquier modelo soportado por tu herramienta simplemente cambiando este campo (e incluso usar modelos distintos por rol).

1.3. Mantén las entradas de Ollama/OpenAI. Cambiar un rol de regreso será tan simple como volver a apuntarlo al proveedor original.

---

## 2. Preparar `Client` para soportar proveedores CLI
2.1. En `Client.__init__` (`scripts/llm.py:1`):
- Lee los campos nuevos `command`, `cwd`, `env` cuando `provider_cfg["type"] == "codex_cli"`.
- Persiste en atributos como `self.cli_command`, `self.cli_cwd`, `self.cli_env`.

2.2. ✅ IMPLEMENTADO: Añadido método `_codex_cli_chat(system: str, user: str) -> str` que:
- Construye argumentos dinámicamente: `["codex", "chat", "--model", self.model, ...]`
- Soporta dos formatos de entrada configurables en `config.yaml`:
  - `stdin` (por defecto): Envía JSON por stdin con system/user/model/temperature/max_tokens
  - `flags`: Usa `--system` y `--user` flags (asumiendo CLI lo soporta)
- Incluye timing y logging completo a `artifacts/<rol>/last_raw.txt`

2.3. En `chat()`, antes de entrar en las ramas Ollama/OpenAI, chequea:
```python
if self.provider_type == "codex_cli":
    return await asyncio.to_thread(self._codex_cli_chat, system, user)
```
Utilizar `asyncio.to_thread` evita bloquear el loop principal cuando se invoca un comando externo.

2.4. Control de errores:
- Usa `subprocess.run(..., capture_output=True, text=True, timeout=timeout_seconds)`.
- Si `returncode != 0`, registra `stderr`, lanza `RuntimeError(f"CODEX_CLI_FAILED: {stderr[:200]}")`.
- En caso de `TimeoutExpired`, lanza una excepción marcada (p.ej. `RuntimeError("CODEX_TIMEOUT")`) para que el orquestador pueda decidir reintentos.

---

## 3. Post-procesar y validar la respuesta del modelo
3.1. Limpieza:
- elimina secuencias ANSI (`\x1b[...]`) si la CLI colorea la salida.
- recorta espacios iniciales/finales.

3.2. Validación:
- comprueba que la respuesta no esté vacía.
- Opcional: para los roles con formato rígido (Dev JSON, BA/Architect YAML, QA markdown), corre validaciones básicas antes de devolver el texto a los scripts consumidores para reducir fallas down-stream.

3.3. Logging:
- Guarda la respuesta cruda en `artifacts/<rol>/last_raw.txt` (por ejemplo `artifacts/dev/last_raw.txt`). Si decides centralizarlo, crea un helper en `scripts/common.py`.

---

## 4. Ajustar la tolerancia a fallos del orquestador
4.1. En `scripts/orchestrate.py:1`, intercepta excepciones provenientes de `_codex_cli_chat` (por ejemplo buscando el prefijo `CODEX_`). Ajusta el mecanismo de reintentos (`story_iteration_count`) para distinguir:
- errores recuperables (timeout, salida no parseable) → reintento automático.
- errores graves (CLI no encontrado) → marcar historia como `blocked_fatal`.

4.2. Usa `append_note` para anotar eventos relevantes (timeout, CLI fail) en `planning/notes.md` con sellos de tiempo.

---

## 5. Documentar e instrumentar
5.1. Añade al `README.md` una subsección “Codex CLI (CLI local)” describiendo:
- Requisitos (instalar la CLI, verificar `codex chat --model codex-local` o el flag que corresponda).
- Cómo se alterna el provider editando `config.yaml`.

5.2. Si el CLI permite modo JSON nativo, documenta el flag y actívalo en los prompts/llm.

5.3. Introduce métrica ligera:
- Alrededor de `_codex_cli_chat`, mide duración (`time.perf_counter`).
- Anexa el tiempo y longitud de respuesta en `artifacts/notes.md`.

---

## 6. Testing exhaustivo
6.1. Pruebas unitarias (opcional pero útil):
- Mockea `subprocess.run` para asegurar que `_codex_cli_chat` construye los flags correctos y maneja errores.

6.2. Smoke tests manuales por rol:
```bash
make setup
CONCEPT="Login MVP" make ba
CONCEPT="Login MVP" make plan
make dev STORY=S1
make qa
```
- Verifica que cada script lea el nuevo provider y que los artefactos (`debug_ba_response.txt`, `artifacts/dev/last_files.json`, etc.) contengan respuestas emitidas por tu CLI.

6.3. Ensayo orquestado:
```bash
ALLOW_NO_TESTS=1 MAX_LOOPS=3 make loop
```
- Observa cómo se comportan los reintentos y asegúrate de que las excepciones CLI no detienen todo el ciclo.

---

## 7. Operación diaria y fallback
- Mantén el CLI versionado (por ejemplo agregando pasos al target `setup` del `Makefile` para instalar o validar la versión deseada).
- Si la CLI deja de responder, vuelve a apuntar los roles a `ollama`/`openai` en `config.yaml` sin revertir el resto del código.
- Documenta en `planning/notes.md` cualquier ajuste de parámetros (`temperature`, `max_tokens`) que hagas tras las primeras ejecuciones para que el equipo entienda el comportamiento del modelo local.

---

## 8. Checklist final antes de desplegar
- [x] `config.yaml` actualizado con el nuevo proveedor y configuración detallada.
- [x] `_codex_cli_chat` implementado con manejo robusto de errores y timeout.
- [x] Logs/artefactos verificados para cada rol (timing, success/failure logging).
- [x] Documentación actualizada (README, este `codex-provider.md`).
- [x] Pruebas básicas creadas (`scripts/test_codex_cli.py`).
- [x] Manejo de errores CLI integrado en orquestador.
- [x] Plan de rollback preparado (revertir roles a provider previo).
- [x] Integración completa con pipeline existente.
