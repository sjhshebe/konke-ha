#!/bin/sh
set -eu

SCRIPT_URL="https://raw.githubusercontent.com/${KONKE_REPO:-sjhshebe/konke-homeassistant}/${KONKE_BRANCH:-main}/install.sh"
TMP_SCRIPT="${TMPDIR:-/tmp}/konke-homeassistant-install.sh"

echo "Updating Konke Smart integration..."

if command -v curl >/dev/null 2>&1; then
  if curl -fsSL --http1.1 "$SCRIPT_URL" -o "$TMP_SCRIPT"; then
    KONKE_ACTION=update sh "$TMP_SCRIPT"
    rm -f "$TMP_SCRIPT"
    exit $?
  fi
  echo "curl download failed; trying wget..."
fi

if command -v wget >/dev/null 2>&1; then
  wget -q "$SCRIPT_URL" -O "$TMP_SCRIPT"
  KONKE_ACTION=update sh "$TMP_SCRIPT"
  rm -f "$TMP_SCRIPT"
  exit $?
fi

echo "curl or wget is required."
exit 1
