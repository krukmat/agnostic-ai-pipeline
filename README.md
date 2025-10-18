# Agnostic AI Pipeline (Arquitecto → Dev → QA)
Pipeline multi-agente, agnóstico al stack, basado en modelos abiertos (Ollama) con opción de usar modelos pagos (OpenAI/LiteLLM).

## Requisitos
- Python 3.10+
- pip y venv
- Ollama local (puerto 11434)
- (Opcional) OPENAI_API_KEY / OPENAI_API_BASE

## Modelos recomendados
    ollama pull llama3.1:8b-instruct
    ollama pull qwen2.5-coder:7b
    ollama pull qwen2.5:7b-instruct

## Instalación
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Uso
    CONCEPT="Carrito de compras: web Express, backend FastAPI, app RN Android" make plan
    make dev
    make qa
    MAX_LOOPS=3 make loop

## Config rápida
    make show-config
    make set-role role=dev provider=ollama model="qwen2.5-coder:14b"
    make set-role role=qa provider=openai model="gpt-4o-mini"
    make set-quality profile=low|normal|high

## Archivo .gitignore
El archivo `.gitignore` ignora archivos de entorno y artefactos temporales:
- Archivos compilados de Python (`__pycache__/`, `*.pyc`)
- Entornos virtuales (`venv/`, `.env`)
- Dependencias de Node.js (`node_modules/`)
- Archivos de IDE (`.vscode/`, `.idea/`)
- Logs y bases de datos temporales (`*.log`, `*.db`)
- Artefactos generados del pipeline (`artifacts/`)
- Backups y archivos temporales
