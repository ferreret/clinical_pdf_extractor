FROM python:3.11-slim

WORKDIR /app

# Evitar prompts interactivos y mejorar logs
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Install system dependencies required for pdf2image (poppler-utils) + curl for HEALTHCHECK
RUN apt-get update && apt-get install -y \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# (Opcional) crear usuario no root
RUN useradd -m appuser
USER appuser

# Copiar requirements e instalar dependencias
COPY --chown=appuser:appuser requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY --chown=appuser:appuser . .

EXPOSE 8501

# Healthcheck: puedes usar /_stcore/health o /healthz según versión de Streamlit
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
