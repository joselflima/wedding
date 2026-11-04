FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-cache
RUN useradd --create-home wedding
COPY --chown=wedding:wedding . .
WORKDIR /app/src
USER wedding
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
