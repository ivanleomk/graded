FROM python:3.11-slim

WORKDIR /app

# Install minimal tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install graded (which pulls in pydantic, instructor, etc.)
RUN pip install --no-cache-dir graded
