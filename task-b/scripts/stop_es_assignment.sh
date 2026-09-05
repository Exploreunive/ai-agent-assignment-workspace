#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.es.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "No assignment Elasticsearch pid file"
  exit 0
fi

pid="$(cat "$PID_FILE")"
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  echo "Stopped Elasticsearch process $pid"
else
  echo "Elasticsearch process $pid is not running"
fi
