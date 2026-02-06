
# Use lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY scripts/ scripts/
COPY data/ data/
COPY models/ models/
COPY .env.template .env

# Set python path
ENV PYTHONPATH=/app

# Default command (can be overridden in docker-compose)
CMD ["python", "src/bot/main.py"]
