#!/bin/sh
# Baut dist/umbauplan-claude.zip (Skill-Ordner mit SKILL.md) zum Hochladen in claude.ai.
set -ef  # -f: Muster in AUSSER nicht von der Shell auflösen lassen
cd "$(dirname "$0")"
mkdir -p dist && rm -f dist/umbauplan-chatgpt.zip dist/umbauplan-claude.zip
AUSSER='*/__pycache__/* *.pyc *.DS_Store'
(cd plugins/umbauplan/skills && zip -qr -X ../../../dist/umbauplan-claude.zip umbauplan -x $AUSSER)
ls -l dist
