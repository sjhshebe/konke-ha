#!/bin/sh
set -eu

SCRIPT_URL="https://raw.githubusercontent.com/${KONKE_REPO:-sjhshebe/konke-homeassistant}/${KONKE_BRANCH:-main}/install.sh"

echo "Updating Konke Smart integration..."

if command -v curl >/dev/null 2>&1; then
  if curl -fsSL "$SCRIPT_URL" | KONKE_ACTION=update sh; then
    exit 0
  fi
  echo "curl download failed; trying wget..."
fi

if command -v wget >/dev/null 2>&1; then
  wget -qO- "$SCRIPT_URL" | KONKE_ACTION=update sh
  exit 0
fi

echo "curl or wget is required."
exit 1
