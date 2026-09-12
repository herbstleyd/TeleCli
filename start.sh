#!/bin/bash
# Startskript für Telecli
# Lädt .env-Datei falls vorhanden und startet die App

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$HOME/.config/telecli/.env"

# .env laden falls vorhanden
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

python3 "$SCRIPT_DIR/telecli.py"
