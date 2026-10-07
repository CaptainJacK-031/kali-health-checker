#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Create the virtual environment first: python3 -m venv .venv"
  exit 1
fi
source .venv/bin/activate
exec uvicorn app.main:app --host 127.0.0.1 --port 8000
