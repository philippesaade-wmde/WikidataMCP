# Use the official Python image from the Docker Hub
FROM ubuntu:22.04

# Install essential packages from ubuntu repository
RUN apt-get update -y && \
    apt-get install -y curl && \
    apt-get install -y python3 python3-pip python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Setup the app in workspace
WORKDIR /workspace

# Install backend dependencies
COPY --chmod=755 requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy backend for production
COPY --chmod=755 . .

# Container startup script
CMD [ "./start.sh" ]