#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ES_URL:-http://127.0.0.1:19200}"
ES_HOME="${ES_HOME:-}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_HOME="$ROOT_DIR/.es-data"
LOG_HOME="$ROOT_DIR/.es-logs"
PID_FILE="$ROOT_DIR/.es.pid"

if [ -z "$ES_HOME" ]; then
  echo "请设置 ES_HOME，例如：ES_HOME=/path/to/elasticsearch-9.4.2 $0" >&2
  exit 1
fi

if [ ! -x "$ES_HOME/bin/elasticsearch" ]; then
  echo "ES_HOME 无效，找不到 $ES_HOME/bin/elasticsearch" >&2
  exit 1
fi

if curl -fsS --max-time 2 "$ES_URL" >/dev/null 2>&1; then
  echo "Elasticsearch already serves $ES_URL"
  exit 0
fi

mkdir -p "$DATA_HOME" "$LOG_HOME"
nohup "$ES_HOME/bin/elasticsearch" \
  -Epath.data="$DATA_HOME" \
  -Epath.logs="$LOG_HOME" \
  -Ehttp.port=19200 \
  -Etransport.port=19300 \
  > "$LOG_HOME/console.log" 2>&1 < /dev/null &
echo $! > "$PID_FILE"

for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
  if curl -fsS --max-time 2 "$ES_URL" >/dev/null 2>&1; then
    echo "Elasticsearch is ready at $ES_URL"
    exit 0
  fi
  sleep 2
done

echo "Elasticsearch did not become ready; see $LOG_HOME/console.log" >&2
exit 1
