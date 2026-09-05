#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ES_URL:-http://127.0.0.1:19200}"
INDEX_NAME="${INDEX_NAME:-agent_assignment_documents}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_FILE="$ROOT_DIR/data/professional_documents.ndjson"

curl --fail --silent --show-error "$ES_URL/$INDEX_NAME" -X DELETE >/dev/null 2>&1 || true

curl --fail --silent --show-error "$ES_URL/$INDEX_NAME" \
  -X PUT \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  },
  "mappings": {
    "properties": {
      "document_id": {"type": "keyword"},
      "version": {"type": "keyword"},
      "title": {"type": "text"},
      "section": {"type": "keyword"},
      "page": {"type": "integer"},
      "allowed_groups": {"type": "keyword"},
      "valid_from": {"type": "date", "format": "yyyy-MM-dd"},
      "valid_to": {"type": "date", "format": "yyyy-MM-dd"},
      "content": {"type": "text"}
    }
  }
}
JSON

curl --fail --silent --show-error "$ES_URL/_bulk" \
  -X POST \
  -H 'Content-Type: application/x-ndjson' \
  --data-binary @"$DATA_FILE"

curl --fail --silent --show-error "$ES_URL/$INDEX_NAME/_refresh" -X POST >/dev/null

printf '\nIndexed documents:\n'
curl --fail --silent --show-error "$ES_URL/$INDEX_NAME/_count"
