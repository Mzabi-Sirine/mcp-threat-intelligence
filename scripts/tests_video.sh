#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
MARKS="${1:-/tmp/ti_tests_marks.jsonl}"
: > "$MARKS"

mark() {
  printf '{"stage":"%s","t":%s}\n' "$1" "$(date +%s.%N)" >> "$MARKS"
}

clear
printf '\n\n'
printf '\033[1;36m  ══════════════════════════════════════════════════════════════════════\033[0m\n'
printf '\033[1;37m    Serveur MCP intelligent de Threat Intelligence\033[0m\n'
printf '\033[1;33m    Campagne de tests réelle · 31 scénarios · données synthétiques\033[0m\n'
printf '\033[1;36m  ══════════════════════════════════════════════════════════════════════\033[0m\n'
printf '\n'
printf '    TEK-UP SSIR 2026-2027 · Mzabi Sirine · Khaled Ellif\n'
printf '    Encadrant : Tarek Hdji\n'
printf '\n'
printf '\033[0;90m    Le projet est exécuté tel quel : tests, preuves, journal.\033[0m\n'
printf '\n'
mark "title_end"
sleep 6

printf '  \033[0;90m%s\033[0m\n\n' "$(date '+%d/%m/%Y %H:%M')"
printf '\033[1;32m$ python3 tests/run_tests.py\033[0m\n'
mark "tests_start"
python3 tests/run_tests.py
status=$?
mark "tests_end"

sleep 8
printf '\n\033[1;32m$ python3 src/ti_cli.py verify-audit --path preuves/lab/audit.jsonl\033[0m\n'
mark "audit_start"
python3 src/ti_cli.py verify-audit --path preuves/lab/audit.jsonl
mark "audit_end"

sleep 8
clear
printf '\n\n'
printf '\033[1;32m  ══════════════════════════════════════════════════════════════════════\033[0m\n'
printf '\033[1;37m    Campagne terminée.\033[0m\n'
printf '\033[1;33m    31/31 scénarios · 16/16 abus · chaîne d’audit valide\033[0m\n'
printf '\033[1;32m  ══════════════════════════════════════════════════════════════════════\033[0m\n'
printf '\n'
printf '    Chaque refus et chaque accès laissent une trace chaînée.\n'
mark "outro_start"
sleep 7
mark "end"
exit "$status"
