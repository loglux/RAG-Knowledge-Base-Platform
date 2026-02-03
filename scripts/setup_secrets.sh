#!/usr/bin/env sh
set -eu

SECRETS_DIR="${SECRETS_DIR:-./secrets}"
SECRET_FILE="${SECRET_FILE:-$SECRETS_DIR/db_password}"

mkdir -p "$SECRETS_DIR"

if [ -f "$SECRET_FILE" ]; then
  echo "Secret file already exists: $SECRET_FILE"
  printf "Overwrite it? [y/N]: "
  read -r confirm
  case "$confirm" in
    y|Y) ;;
    *) echo "Aborted."; exit 0 ;;
  esac
fi

printf "Enter current DB password: "
stty -echo
read -r password
stty echo
printf "\n"

if [ -z "$password" ]; then
  echo "Password cannot be empty."
  exit 1
fi

umask 077
printf "%s" "$password" > "$SECRET_FILE"
chmod 600 "$SECRET_FILE"

echo "✅ Secret written to $SECRET_FILE"
echo "Next: docker compose down && docker compose up -d --build"
