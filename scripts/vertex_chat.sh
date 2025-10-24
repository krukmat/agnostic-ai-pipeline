#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-${GCP_PROJECT:?set GCP_PROJECT or PROJECT_ID}}"
LOCATION="${LOCATION:-${VERTEX_LOCATION:-us-central1}}"
MODEL="${MODEL:-${VERTEX_MODEL:-gemini-2.5-flash}}"
PROMPT="${1:-Hello from Vertex AI}"

read -r -d '' BODY <<JSON || true
{
  "contents": [{
    "role": "user",
    "parts": [{"text": "$PROMPT"}]
  }],
  "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256}
}
JSON

curl -sS -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL}:generateContent" \
  -d "$BODY"
