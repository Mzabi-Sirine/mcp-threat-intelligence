#!/usr/bin/env bash
# Lancement du serveur MCP en stdio, sans dépendance externe.
set -euo pipefail
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$PROJECT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "${PYTHON:-python3}" -m ti_server
