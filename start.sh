#!/bin/bash

set -e

set -a
if [ -f .env ]; then
  source .env
fi
set +a

cd /workspace

echo "Starting MCP"
exec uv run python3 main.py
