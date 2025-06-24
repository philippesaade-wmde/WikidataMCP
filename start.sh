#!/bin/bash

set -e

set -a
source .env
set +a

cd /workspace

echo "Starting MCP"
exec python3 MCP/server.py