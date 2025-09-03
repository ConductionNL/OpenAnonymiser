FROM python:3.12.11-slim-bookworm

# use the latest version of uv from the official repository
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN groupadd -r presidio && useradd --no-log-init -r -g presidio presidio

WORKDIR /app

# Create necessary directories and set permissions
RUN mkdir -p /home/presidio/.cache/uv && \
    chown -R presidio:presidio /home/presidio/.cache && \
    chown -R presidio:presidio /app

COPY --chown=presidio:presidio pyproject.toml uv.lock ./

USER presidio

# Disable UV cache for runtime (read-only filesystem in K8s)
ENV UV_NO_CACHE=1

# resolve from uv.lock only, no dev dependencies
RUN uv sync --frozen --no-dev --no-cache

COPY --chown=presidio:presidio src/api ./src/api
COPY --chown=presidio:presidio api.py ./
COPY --chown=presidio:presidio scripts/healthcheck.py ./scripts/

# Pre-download transformers models during build to avoid runtime download
ENV TRANSFORMERS_CACHE=/home/presidio/.cache/transformers
ENV HF_HOME=/home/presidio/.cache/huggingface
RUN mkdir -p /home/presidio/.cache/transformers /home/presidio/.cache/huggingface && \
    chown -R presidio:presidio /home/presidio/.cache

# Download the Dutch RoBERTa model during build
RUN .venv/bin/python -c "from transformers import AutoTokenizer, AutoModelForTokenClassification; \
    model_name = 'pdelobelle/robbert-v2-dutch-base'; \
    print(f'Downloading {model_name}...'); \
    tokenizer = AutoTokenizer.from_pretrained(model_name); \
    model = AutoModelForTokenClassification.from_pretrained(model_name); \
    print('Model downloaded successfully!')"

EXPOSE 8080

# Add Docker healthcheck
HEALTHCHECK \
    --interval=60s \
    --timeout=5s \
    --start-period=25s \
    --retries=5 \
  CMD [".venv/bin/python", "scripts/healthcheck.py", "--port", "8080"]

CMD [".venv/bin/python", "api.py", "--host", "0.0.0.0", "--workers", "2", "--env", "production", "--port", "8080"]