COMPOSE := docker compose --env-file .env.local -f compose.yaml

DOCKER_DESKTOP_BIN := /Applications/Docker.app/Contents/Resources/bin
ifneq ($(wildcard $(DOCKER_DESKTOP_BIN)/docker-credential-desktop),)
export PATH := $(PATH):$(DOCKER_DESKTOP_BIN)
endif

.PHONY: up rebuild

up: .env.local
	$(COMPOSE) build web
	$(COMPOSE) up -d db
	$(COMPOSE) run --rm web python manage.py migrate --noinput
	$(COMPOSE) up -d web

rebuild: .env.local
	$(COMPOSE) up -d --build web

.env.local:
	python3 scripts/init_env.py
