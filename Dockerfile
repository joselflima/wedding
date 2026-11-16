FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.10 /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY src ./src
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app/src
RUN DJANGO_SECRET_KEY=build-only MYSQL_DATABASE=build MYSQL_USER=build MYSQL_PASSWORD=build python manage.py collectstatic --noinput
RUN useradd --system django
USER django
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--access-logfile", "-"]
