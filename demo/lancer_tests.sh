#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
LOG="preuves/logs/console_tests_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p preuves/logs
exec > >(tee "$LOG") 2>&1
printf '%s\n' "=============================================================="
printf '%s\n' " TEK-UP SSIR - MCP Threat Intelligence - CAMPAGNE DE TESTS REELLE"
printf '%s\n' " Machine : $(hostname) · $(date '+%d/%m/%Y %H:%M')"
printf '%s\n' " Dossier : $(pwd)"
printf '%s\n' "=============================================================="
echo
echo "31 scenarios : N01-N15 (nominal + durcissement), A01-A16 (abus)"
echo
date '+%Y-%m-%dT%H:%M:%S' > preuves/logs/lancer_tests_started.flag
python3 -u tests/run_tests.py
status=$?
echo
echo "--- Verification de la chaine d'audit ---"
python3 src/ti_cli.py verify-audit --path preuves/lab/audit.jsonl
echo
echo "Code de sortie de la campagne : $status (0 = succes)"
echo "Transcription conservee : $LOG"
echo
echo "Appuyez sur Entree pour fermer cette fenetre..."
read -r _ || true
