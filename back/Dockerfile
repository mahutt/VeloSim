FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Configuring Backend Container
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    libexpat1 && \
    rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and the source code needed for installation
COPY pyproject.toml ./
COPY back/ ./back
COPY sim/ ./sim
COPY grafana_logging/ ./grafana_logging

# Install the package with all dependencies
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir .

# Copy remaining files into container.
COPY scripts/ ./scripts

# Extract traffic templates from the bundled archive.
RUN python scripts/extract_traffic_templates.py

ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "back.main:app", "--host", "0.0.0.0", "--port", "8000"]
