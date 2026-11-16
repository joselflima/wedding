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

Para subir o ambiente local e reconstruir a imagem:

```sh
docker compose --env-file .env.local -f compose.yaml up --build
```

Com o ambiente em execução, use outro terminal para aplicar as migrações e criar o superadministrador do Django local:

```sh
docker compose --env-file .env.local -f compose.yaml exec web python manage.py migrate --noinput
docker compose --env-file .env.local -f compose.yaml exec web python manage.py createsuperuser
```

Informe `--env-file .env.local` para que o Compose preencha também as variáveis do arquivo YAML.

## Produção

Consulte [implantação](docs/deployment.md). Segredos nunca devem ser versionados.

Pushes na `main` executam validações no GitHub Actions e, após sucesso, atualizam a VPS por SSH. Consulte a seção de deploy automático em [implantação](docs/deployment.md).

## Atualização de bancos com o usuário padrão do Django

Se `admin.0001_initial` já foi aplicada antes da introdução do `User`
customizado, `migrate` acusará `InconsistentMigrationHistory`.
Faça um backup do MySQL e interrompa a aplicação durante a atualização.
Reconstrua a imagem com o código atual e execute, nesta ordem:

```sh
docker compose --env-file .env.local build web
docker compose --env-file .env.local run --rm web python manage.py adopt_legacy_users
docker compose --env-file .env.local run --rm web python manage.py migrate --noinput
docker compose --env-file .env.local up -d web
```

A adoção reutiliza `auth_user`, preservando IDs, hashes de senha, permissões,
grupos e referências do Admin. Os nomes são derivados do nome anterior ou do
usuário. As contas existentes recebem tipo Convidado, sem promoção automática
a noivo; privilégios administrativos existentes são preservados. O email antigo
é removido. O comando é específico para MySQL; bancos novos usam apenas `migrate`.
Não apague o volume nem use `migrate --fake` para contornar o erro.
