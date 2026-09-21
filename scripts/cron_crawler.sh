#!/usr/bin/env bash
# ==============================================================================
# 🇧🇷 STF Transparency Platform — Scheduled Incremental Crawler
#
# Usage:
#   ./scripts/cron_crawler.sh
#
# Recommended crontab (runs daily at 02:00 AM):
#   0 2 * * * /home/gabrielcarmonapy/Desktop/sft_data/scripts/cron_crawler.sh >> /home/gabrielcarmonapy/Desktop/sft_data/data/logs/crawler.log 2>&1
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_ROOT/data/logs"
LOCK_FILE="/tmp/stf_crawler.lock"

mkdir -p "$LOGS_DIR"

echo "=========================================================="
echo " STF Incremental Crawler Started: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo " Project Root: $PROJECT_ROOT"
echo "=========================================================="

# Ensure single execution with flock
exec 200>"$LOCK_FILE"
flock -n 200 || {
    echo "⚠️ Crawler is already running. Exiting."
    exit 0
}

cd "$PROJECT_ROOT"

# Use virtualenv python if present
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

# Run incremental crawler
$PYTHON -m ingestion.crawler --dataset all --batch-size 50

# Run automated quality assertions on newly updated data
$PYTHON -m quality.runner

echo "=========================================================="
echo " STF Incremental Crawler Finished: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=========================================================="

