#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
DELAY="${1:-17}"

clear
printf '\n\n'
printf '\033[1;36m  ══════════════════════════════════════════════════════════════════════\033[0m\n'
printf '\033[1;37m    Serveur MCP intelligent de Threat Intelligence\033[0m\n'
printf '\033[1;33m    Démonstration live · 7 scènes · données synthétiques\033[0m\n'
printf '\033[1;36m  ══════════════════════════════════════════════════════════════════════\033[0m\n'
printf '\n'
printf '    TEK-UP SSIR 2026-2027 · Mzabi Sirine · Khaled Ellif\n'
printf '    Encadrant : Tarek Hdji\n'
printf '\n'
printf '\033[0;90m    Le terminal joue la démonstration automatiquement.\033[0m\n'
sleep 6

python3 scripts/demo_defense.py --present --auto-delay "$DELAY"
status=$?

sleep 9
clear
printf '\n\n'
printf '\033[1;32m  ══════════════════════════════════════════════════════════════════════\033[0m\n'
printf '\033[1;37m    Démonstration terminée.\033[0m\n'
printf '\033[1;33m    Chaque refus et chaque accès laissent une trace chaînée.\033[0m\n'
printf '\033[1;32m  ══════════════════════════════════════════════════════════════════════\033[0m\n'
sleep 7
exit "$status"
