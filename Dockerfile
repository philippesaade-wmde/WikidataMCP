FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /uvx /bin/

# Setup the app in workspace
WORKDIR /workspace

# Install backend dependencies
COPY --chmod=755 pyproject.toml .
COPY --chmod=755 uv.lock .
RUN uv sync

# Copy backend for production
COPY --chmod=755 . .

# Container start script
CMD [ "uv", "run", "main.py" ]