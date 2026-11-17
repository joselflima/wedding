# Repository Guidelines

## Estrutura e organização

O Wedding é uma aplicação pessoal de planejamento de casamento, com foco nos noivos, convidados e padrinhos. Usa Python 3.13, Django 5.2 e MySQL 8.4.

- `src/config/`: configurações, URLs e entradas WSGI/ASGI.
- `src/wedding/`: modelos, views, Admin, migrações e comandos de gestão.
- `src/wedding/tests.py`: testes automatizados.
- `src/wedding/templates/` e `src/wedding/static/`: templates, CSS, JavaScript e fontes.
- `scripts/`: preparação do ambiente e deploy; `docs/deployment.md`: operação da VPS.
- `compose.yaml`: ambiente local; `compose.vps.yaml`: produção; `.github/workflows/main.yml`: validação e deploy.

## Desenvolvimento e validação

Execute na raiz, com Docker Compose v2 disponível:

```sh
python3 scripts/init_env.py
docker compose --env-file .env.local build web
docker compose --env-file .env.local up -d db
docker compose --env-file .env.local run --rm web python manage.py migrate --noinput
docker compose --env-file .env.local up -d web
```

O script cria `.env.local` sem substituir um arquivo existente. O build incorpora o código na imagem; reconstrua após alterações. A aplicação fica em `http://localhost:8000/`; o Admin, em `/admin/`.

Verifique migrações pendentes com:

```sh
docker compose --env-file .env.local run --rm web python manage.py makemigrations --check --dry-run
```

## Estilo e nomenclatura

Use quatro espaços em Python, `snake_case` para funções e variáveis e `PascalCase` para classes. Mantenha templates e assets no namespace `wedding`. Gere migrações pelo Django ao alterar modelos. Não há formatter ou linter configurado; siga o estilo do arquivo e evite reformatações alheias à tarefa. Escreva documentação e textos da interface em português.

## Testes

Use `django.test.TestCase`, classes terminadas em `Tests` e métodos `test_*`. Cubra permissões, autenticação, restrições dos modelos e regressões. Não existe meta numérica de cobertura configurada. Execute como no CI, usando root para criar o banco temporário:

```sh
docker compose --env-file .env.local run --rm -e MYSQL_USER=root web sh -c 'MYSQL_PASSWORD="$MYSQL_ROOT_PASSWORD" python manage.py test'
```

## Commits e pull requests

O histórico combina descrições diretas e prefixos como `feat:`. Prefira commits pequenos com mensagens claras. Nos PRs, descreva o comportamento alterado, validações executadas, migrações necessárias e issues relacionadas; inclua capturas para mudanças visuais. Pushes na `main` disparam deploy após validação.

## Segurança e dados

Nunca versione segredos. Preserve o volume MySQL; `down -v` apaga dados. Valide permissões no backend. Para bancos legados, siga o procedimento de backup e adoção em `README.md` antes de migrar.
