#!/bin/sh
# Baut je Skill eine ZIP zum Hochladen in claude.ai: dist/<skill>-claude.zip mit SKILL.md und einer
# Kopie des gemeinsamen Ordners plankern/ (im Plugin liegt er nur einmal, unter plugins/umbauteam/plankern).
set -ef  # -f: Muster in AUSSER nicht von der Shell auflösen lassen
cd "$(dirname "$0")"
SKILLS="kuechenplan badplan gesamtplan"
mkdir -p dist && rm -f dist/umbauplan-claude.zip dist/umbauplan-chatgpt.zip
for skill in $SKILLS; do rm -f "dist/$skill-claude.zip"; done
AUSSER='*/__pycache__/* *.pyc *.DS_Store'
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
for skill in $SKILLS; do
  mkdir -p "$TMP/$skill"
  cp plugins/umbauteam/skills/$skill/SKILL.md "$TMP/$skill/"
  cp -R plugins/umbauteam/plankern "$TMP/$skill/plankern"
  (cd "$TMP" && zip -qr -X "$OLDPWD/dist/$skill-claude.zip" "$skill" -x $AUSSER)
done
for skill in $SKILLS; do ls -l "dist/$skill-claude.zip"; done
