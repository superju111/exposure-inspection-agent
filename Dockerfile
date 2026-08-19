# Dockerfile for exposure-inspection-agent
# Builds a minimal Python container that runs the agent cycle
# This container is managed by agent-compose's guest runtime

FROM python:3.12-slim

LABEL maintainer="exposure-inspection-agent"
LABEL description="Internet exposure surface inspection agent"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and knowledge files
COPY src/ /app/src/
COPY knowledge/ /app/knowledge/
COPY sample-data/ /app/sample-data/

# Create output directory
RUN mkdir -p /data/output/logs

# Set environment defaults
ENV PYTHONUNBUFFERED=1
ENV KNOWLEDGE_DIR=/app/knowledge
ENV OUTPUT_DIR=/data/output

# Health check: verify Python can import config module
HEALTHCHECK --interval=60s --timeout=10s --retries=3 --start-period=10s \
    CMD python3 -c "import sys; sys.path.insert(0,'/app/src'); import config; print('ok')" || exit 1

# Entry point: run the agent cycle
# agent-compose's daemon calls this via the guest container
ENTRYPOINT ["python3", "/app/src/main.py"]
