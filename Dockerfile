# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Upgrade the pip version to the most recent version
RUN pip install --upgrade pip

# Setup the app in workspace
WORKDIR /workspace

# Install backend dependencies
COPY --chmod=755 requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy backend for production
COPY --chmod=755 . .

# Container start script
CMD [ "python", "MCP/server.py" ]