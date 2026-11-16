# Wedding

Base Django para planejamento pessoal de casamento. Atualmente contém apenas o Admin; listas e perfis ainda não estão implementados.

## Simulação local de produção

Requer Docker Compose v2 e Python 3.13. Gunicorn, WhiteNoise e MySQL são os mesmos componentes usados na VPS; HTTPS fica a cargo do Traefik somente na VPS.

```sh
python3 scripts/init_env.py
docker compose --env-file .env.local build web
docker compose --env-file .env.local up -d db
docker compose --env-file .env.local run --rm web python manage.py migrate --noinput
docker compose --env-file .env.local run --rm web python manage.py createsuperuser
docker compose --env-file .env.local up -d web
```

Acesse http://localhost:8000/admin/ e /health/. O volume wedding_local_mysql_data mantém os dados. Não use `down -v` se quiser preservá-los.

## Produção

Consulte [implantação](docs/deployment.md). Segredos nunca devem ser versionados.

Pushes na `main` executam validações no GitHub Actions e, após sucesso, atualizam a VPS por SSH. Consulte a seção de deploy automático em [implantação](docs/deployment.md).
