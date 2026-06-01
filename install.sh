#!/bin/sh
set -eu

REPO="${KONKE_REPO:-sjhshebe/konke-homeassistant}"
BRANCH="${KONKE_BRANCH:-main}"
ACTION="${KONKE_ACTION:-install}"
TMP_BASE="${TMPDIR:-/tmp}"
WORK_DIR="$TMP_BASE/konke-homeassistant-install"
ARCHIVE="$TMP_BASE/konke-homeassistant-$BRANCH.tar.gz"
ARCHIVE_URL="https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz"

if [ -n "${KONKE_HA_CONFIG_DIR:-}" ]; then
  CONFIG_DIR="$KONKE_HA_CONFIG_DIR"
elif [ -d /config ]; then
  CONFIG_DIR="/config"
elif [ -d /mnt/data/supervisor/homeassistant ]; then
  CONFIG_DIR="/mnt/data/supervisor/homeassistant"
else
  echo "Unable to find Home Assistant config directory."
  echo "Set KONKE_HA_CONFIG_DIR=/path/to/config and run this script again."
  exit 1
fi

TARGET_DIR="$CONFIG_DIR/custom_components/konke"
BACKUP_DIR="$CONFIG_DIR/konke-backups"

download() {
  if command -v curl >/dev/null 2>&1; then
    if curl -fsSL "$ARCHIVE_URL" -o "$ARCHIVE"; then
      return
    fi
    echo "curl download failed; trying wget..."
  fi

  if command -v wget >/dev/null 2>&1; then
    wget -q "$ARCHIVE_URL" -O "$ARCHIVE"
    return
  fi

  echo "curl or wget is required."
  exit 1
}

echo "Running Konke Smart $ACTION from $REPO ($BRANCH)..."
echo "Home Assistant config directory: $CONFIG_DIR"

rm -rf "$WORK_DIR" "$ARCHIVE"
mkdir -p "$WORK_DIR" "$CONFIG_DIR/custom_components"

download
tar -xzf "$ARCHIVE" -C "$WORK_DIR"

SOURCE_DIR="$(find "$WORK_DIR" -type d -path '*/custom_components/konke' | head -n 1)"
if [ -z "$SOURCE_DIR" ] || [ ! -d "$SOURCE_DIR" ]; then
  echo "Downloaded package does not contain custom_components/konke."
  exit 1
fi

if [ -d "$TARGET_DIR" ]; then
  mkdir -p "$BACKUP_DIR"
  BACKUP_FILE="$BACKUP_DIR/konke-before-$ACTION-$(date +%Y%m%d-%H%M%S).tar.gz"
  tar -czf "$BACKUP_FILE" -C "$CONFIG_DIR/custom_components" konke
  echo "Existing integration backed up to $BACKUP_FILE"
  rm -rf "$TARGET_DIR"
fi

cp -R "$SOURCE_DIR" "$TARGET_DIR"
rm -rf "$WORK_DIR" "$ARCHIVE"

echo "Konke Smart integration $ACTION completed: $TARGET_DIR"

if [ "${KONKE_SKIP_RESTART:-0}" = "1" ]; then
  echo "Skipping Home Assistant restart because KONKE_SKIP_RESTART=1."
elif command -v ha >/dev/null 2>&1; then
  echo "Restarting Home Assistant Core..."
  ha core restart
else
  echo "Home Assistant CLI was not found. Please restart Home Assistant manually."
fi
