# Wedding

Aplicação pessoal para planejar um único casamento, com uma lista de convidados compartilhada pelos dois noivos.

## Disponível

- Entrada comum de Maria Eduarda & José Lucas com usuário e senha e logout por POST. Após o login, o perfil da conta determina o destino, independentemente de `next`.
- Páginas iniciais exclusivas por perfil: `/couple/`, `/convidados/` e `/padrinhos/`. A gestão da lista fica em `/noivos/convidados/`, acessível pelo início dos noivos.
- Lista de convidados exclusiva dos noivos, com cadastro, edição, exclusão confirmada, busca por nome ou telefone, ordenação alfabética e paginação de 25 registros.
- Total geral e quantidade de resultados da busca; estados vazio, sem resultados e mensagens de sucesso.
- Nome obrigatório (200 caracteres), telefone opcional (30) e observações opcionais (2.000). Cada registro representa uma pessoa; nomes repetidos são permitidos. Cadastrar convidados não cria contas.
- Layout responsivo em português: tabela no desktop e cartões no celular.
- No máximo dois usuários com perfil Noivos em todo o banco, garantidos por restrições `UNIQUE` e `CHECK`, inclusive em gravações concorrentes. Contas inativas continuam ocupando sua vaga.
- Comando explícito para criar um noivo de demonstração, sem privilégios administrativos ou convidados fictícios.

Convidados e Padrinhos possuem páginas de acolhimento protegidas por perfil; suas funcionalidades e a lista de padrinhos permanecem planejadas. O espaço `/convidados/` não dá acesso à gestão da lista. Cadastro público, recuperação de senha, gestão de vagas pela interface e implantação na VPS Hostinger não fazem parte desta versão.

## Stack

Python 3.13, Django 5.2.19 LTS, mysqlclient 2.3.0 e MySQL 8.4. Dependências Python são gerenciadas pelo uv: dependências diretas em `pyproject.toml` e resolução completa fixada em `uv.lock`. A versão do Python está definida em `.python-version`. O Docker instala as dependências com `uv sync --locked`. Templates Django e CSS próprio, sem build de frontend. Docker Compose mantém aplicação e banco separados; o MySQL usa volume persistente e não publica porta no host.

## Ambiente virtual com uv

Instale o [uv](https://docs.astral.sh/uv/getting-started/installation/) e execute na raiz:

```sh
uv sync --locked
source .venv/bin/activate
```

O comando cria ou sincroniza `.venv` com Python 3.13 e as dependências do lockfile. A ativação é opcional ao usar `uv run`. O ambiente é ignorado pelo Git e pelo build Docker.

Para compilar `mysqlclient` no macOS, instale as bibliotecas cliente do MySQL e pkg-config:

```sh
brew install mysql-client pkg-config
export PKG_CONFIG_PATH="$(brew --prefix mysql-client)/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
uv sync --locked
```

No Debian/Ubuntu, os pacotes necessários são `build-essential`, `pkg-config`, `default-libmysqlclient-dev` e os headers do Python 3.13. O Docker já instala as dependências de compilação.

Use `uv add pacote` ou `uv remove pacote` para alterar dependências e versione `pyproject.toml` e `uv.lock` juntos. Para atualizar as versões transitivas preservadas nesta migração, ajuste também `constraint-dependencies` em `pyproject.toml`.

## Execução local

Pré-requisitos: Docker Desktop/Engine em execução, Docker Compose v2 e Python 3 para gerar a configuração local.

```sh
python3 scripts/init_env.py
docker compose up -d db
docker compose build web
docker compose run --rm web python manage.py migrate
docker compose up -d web
```

No macOS, caso o Docker informe que `docker-credential-desktop` não foi encontrado, inclua seus utilitários no PATH com `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"` e repita o comando.


O gerador nunca substitui um `.env` existente. Alternativamente, copie `.env.example` para `.env` e preencha os segredos. Configure `APP_PORT` para mudar a porta local e `DJANGO_ALLOWED_HOSTS` se necessário. O Compose espera a saúde do MySQL antes de executar a aplicação.


A aplicação usa Gunicorn e está publicada apenas em `127.0.0.1` para desenvolvimento. A implantação na VPS terá uma etapa própria para servidor de aplicação, HTTPS, estáticos e configuração de produção. Fora de debug, os cookies de sessão e CSRF exigem HTTPS.

## Verificação

A suíte de aceitação roda no MySQL 8.4. O comando abaixo usa o usuário root somente para criar e remover o banco isolado `test_wedding`; o servidor da aplicação usa o usuário restrito `wedding`. Caso personalize `MYSQL_DATABASE`, o banco de teste recebe o prefixo `test_`.

```sh
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web sh -c 'MYSQL_USER=root MYSQL_PASSWORD="$MYSQL_ROOT_PASSWORD" python manage.py test --noinput'
```

Os testes cobrem autorização em todas as rotas e escritas diretas, CSRF, login/logout, CRUD, limites dos campos, busca, paginação, escape HTML, sessões e restrições de vagas. O teste concorrente usa conexões independentes disputando a segunda vaga e exige exatamente um vencedor.

Para verificações rápidas sem MySQL, existe uma configuração isolada com SQLite; ela **não substitui** a aceitação no MySQL e pula o teste concorrente:

```sh
DJANGO_SETTINGS_MODULE=config.test_settings uv run --locked python src/manage.py test src
```

Esse comando usa o ambiente `.venv` gerenciado pelo uv. A configuração normal sempre usa MySQL.

Para verificar persistência, cadastre um convidado e reinicie os serviços:

```sh
docker compose restart db web
```

Aguarde a saúde do banco e confira a lista novamente. `docker compose down` mantém o volume; `docker compose down -v` apaga permanentemente o banco local. Alterar senhas do MySQL no `.env` não modifica usuários de um volume já inicializado.

## Organização e autorização

Todo o código Django fica em `src`, organizado por domínio e recursos compartilhados:

```text
src/
├── manage.py
├── config/             # Settings, URLs globais e WSGI
├── core/
│   ├── guests/         # App Convidados: início do perfil e recurso de gestão restrito aos noivos
│   ├── couple/         # App Noivos: início e acesso à gestão de convidados
│   └── godparents/     # App Padrinhos: início protegido por perfil
└── foundation/
    ├── accounts/       # App compartilhado: usuário, autenticação, perfis e provisionamento
    ├── permissions.py  # Autorização compartilhada (CoupleRequiredMixin)
    ├── templates/      # Base, login e páginas de erro
    └── static/         # CSS compartilhado
```

Os três apps de domínio estão registrados no Django. `couple` e `godparents` possuem rotas e páginas iniciais próprias, sem modelos; seus campos e operações serão definidos nas próximas etapas. Contas de acesso continuam em `foundation/accounts`, separadas dos registros das listas.

Os labels `accounts` e `guests`, as tabelas e o histórico de migrations foram preservados: a reorganização não exige migração de dados. Imports Python usam `foundation.accounts` e `core.guests`.

Dockerfile, Compose, dependências e scripts de infraestrutura permanecem na raiz. O container executa em `/app/src`, portanto os comandos Docker com `python manage.py` continuam válidos. Fora do container, use `python src/manage.py` a partir da raiz; o módulo de configuração é `config.settings` e o WSGI é `config.wsgi.application`. Para descobrir toda a suíte a partir da raiz, use `python src/manage.py test src`; no container, `python manage.py test` já parte de `src`.

A raiz e `/login/` exibem o mesmo login aos visitantes e encaminham contas autenticadas ao início do perfil. Visitantes de rotas protegidas são redirecionados ao login. Contas autenticadas de outros perfis recebem HTTP 403 em todas as operações, mesmo se forem superusuários. Apenas contas ativas com perfil Noivos e vaga 1 ou 2 têm acesso. O painel `/admin/` permite gerenciar contas.

Migrations versionadas criam o esquema; não criam contas nem dados de demonstração. As orientações de contribuição estão em [AGENTS.md](AGENTS.md).

## GitHub Actions

Pushes e pull requests para `main` executam os testes no MySQL. Depois de um push aprovado pelos testes, um workflow reutilizável pode atualizar a VPS por SSH. O deploy permanece desabilitado até configurarmos o servidor e `DEPLOY_ENABLED=true` no GitHub.

O gatilho, o job reutilizável e o script da VPS estão separados. Consulte [docs/deployment.md](docs/deployment.md) para os secrets, variáveis e a preparação de produção ainda pendente.

## Produção com imagem pronta

A imagem usa Gunicorn e WhiteNoise, com estáticos coletados no build.
Para o painel da Hostinger, use o Compose independente `compose.vps.yaml`:
o GitHub publica a imagem no GHCR após os testes, e a VPS baixa a imagem pronta.
Migrations são executadas pelo serviço `init` antes do web; Caddy fornece HTTPS.
Consulte [implantação](docs/deployment.md#implantação-pelo-painel-docker-da-hostinger-ghcr).


### Contas e autenticação

Aplique as migrations com `docker compose exec web python manage.py migrate` antes de criar contas.
Crie o administrador com `docker compose run --rm web python manage.py createsuperuser`.
Acesse `/admin/` para cadastrar contas com perfil e vaga. Apenas superusuários gerenciam contas.
Noivos usam as vagas 1 e 2; convidados e padrinhos deixam a vaga vazia.
O login em `/login/` cria uma sessão Django e encaminha ao início do perfil; o logout exige POST.
Contas das listas não criam usuários automaticamente.
A migração desativa contas de demonstração, inutiliza suas senhas e remove suas sessões,
preservando registros e vagas. Revise essas contas pelo Admin antes de liberar uma vaga.
