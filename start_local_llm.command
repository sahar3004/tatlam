#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

exec ./scripts/start_local_llm.sh "$@"
