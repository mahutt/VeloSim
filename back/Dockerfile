FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY back/requirements.txt /tmp/requirements/back.txt
COPY sim/ /tmp/sim-src

RUN python -m pip install --upgrade pip setuptools wheel \
 && python -m pip install --no-cache-dir -r /tmp/requirements/back.txt \
 && if [ -f /tmp/sim-src/pyproject.toml ] || [ -f /tmp/sim-src/setup.py ]; then \
        python -m pip install /tmp/sim-src; \
    elif [ -f /tmp/sim-src/requirements.txt ]; then \
        python -m pip install -r /tmp/sim-src/requirements.txt; \
    else \
        python -m pip install 'simpy>=4.0.2'; \
    fi

RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client && \
    rm -rf /var/lib/apt/lists/*

COPY back/ ./back
COPY sim/  ./sim

ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "back.main:app", "--host", "0.0.0.0", "--port", "8000"]
