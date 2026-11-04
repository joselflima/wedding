FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home wedding
COPY --chown=wedding:wedding . .
WORKDIR /app/src
USER wedding
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
