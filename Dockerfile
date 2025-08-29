FROM python:3.11-slim

# Force rebuild: 2024-08-29-2250
# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ .

# Expose port (Railway will override with PORT env var)
EXPOSE 8000

# Start command
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]