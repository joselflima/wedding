# Wedding

Aplicação pessoal para planejar um único casamento, com uma lista de convidados compartilhada pelos dois noivos.

## Disponível

- Login com usuário e senha e logout por POST.
- Lista de convidados exclusiva dos noivos, com cadastro, edição, exclusão confirmada, busca por nome ou telefone, ordenação alfabética e paginação de 25 registros.
- Total geral e quantidade de resultados da busca; estados vazio, sem resultados e mensagens de sucesso.
- Nome obrigatório (200 caracteres), telefone opcional (30) e observações opcionais (2.000). Cada registro representa uma pessoa; nomes repetidos são permitidos. Cadastrar convidados não cria contas.
- Layout responsivo em português: tabela no desktop e cartões no celular.
- No máximo dois usuários com perfil Noivos em todo o banco, garantidos por restrições `UNIQUE` e `CHECK`, inclusive em gravações concorrentes. Contas inativas continuam ocupando sua vaga.
- Comando explícito para criar um noivo de demonstração, sem privilégios administrativos ou convidados fictícios.

Perfis Convidados e Padrinhos existem apenas para autorização; suas funcionalidades e a lista de padrinhos permanecem planejadas. Cadastro público, recuperação de senha, gestão de vagas pela interface e implantação na VPS Hostinger não fazem parte desta versão.

## Stack

Python 3.13, Django 5.2.19 LTS, mysqlclient 2.3.0 e MySQL 8.4. Dependências Python diretas e transitivas estão fixadas em `requirements.txt`. Templates Django e CSS próprio, sem build de frontend. Docker Compose mantém aplicação e banco separados; o MySQL usa volume persistente e não publica porta no host.

## Execução local

Pré-requisitos: Docker Desktop/Engine em execução, Docker Compose v2 e Python 3 para gerar a configuração local.

```sh
python3 scripts/init_env.py
docker compose up -d db
docker compose build web
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py provision_demo
docker compose up -d web
```

No macOS, caso o Docker informe que `docker-credential-desktop` não foi encontrado, inclua seus utilitários no PATH com `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"` e repita o comando.

Abra [http://localhost:8000](http://localhost:8000). Use `DEMO_USERNAME` e `DEMO_PASSWORD` do seu `.env`; o login padrão é `noivo_demo` e a senha é gerada individualmente. O arquivo não é versionado. A lista começa vazia.

O gerador nunca substitui um `.env` existente. Alternativamente, copie `.env.example` para `.env` e preencha os segredos. Configure `APP_PORT` para mudar a porta local e `DJANGO_ALLOWED_HOSTS` se necessário. O Compose espera a saúde do MySQL antes de executar a aplicação.

O provisionamento usa hash de senha do Django, valida a senha e ocupa a primeira vaga disponível. Reexecuções com o mesmo usuário de demonstração não alteram senha ou dados existentes. Login de outra conta, demonstração inativa ou duas vagas ocupadas geram erro. Alterar `DEMO_PASSWORD` no `.env` depois do provisionamento não muda a senha já cadastrada; use o comando interativo `docker compose run --rm web python manage.py changepassword noivo_demo` quando necessário.

A aplicação usa `runserver` e está publicada apenas em `127.0.0.1` para desenvolvimento. A implantação na VPS terá uma etapa própria para servidor de aplicação, HTTPS, estáticos e configuração de produção. Fora de debug, os cookies de sessão e CSRF exigem HTTPS.

## Verificação

A suíte de aceitação roda no MySQL 8.4. O comando abaixo usa o usuário root somente para criar e remover o banco isolado `test_wedding`; o servidor da aplicação usa o usuário restrito `wedding`. Caso personalize `MYSQL_DATABASE`, o banco de teste recebe o prefixo `test_`.

```sh
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web sh -c 'MYSQL_USER=root MYSQL_PASSWORD="$MYSQL_ROOT_PASSWORD" python manage.py test --noinput'
```

Os testes cobrem autorização em todas as rotas e escritas diretas, CSRF, login/logout, CRUD, limites dos campos, busca, paginação, escape HTML, provisionamento idempotente e restrições de vagas. O teste concorrente usa conexões independentes disputando a segunda vaga e exige exatamente um vencedor.

Para verificações rápidas sem MySQL, existe uma configuração isolada com SQLite; ela **não substitui** a aceitação no MySQL e pula o teste concorrente:

```sh
DJANGO_SETTINGS_MODULE=config.test_settings .venv/bin/python src/manage.py test src
```

Esse comando opcional pressupõe um ambiente `.venv` com Django e suas dependências instalados. A configuração normal sempre usa MySQL.

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
│   ├── guests/         # App Convidados: modelo, migrations, formulários, views e templates
│   ├── couple/         # App Noivos: estrutura pronta para funcionalidades próprias
│   └── godparents/     # App Padrinhos: estrutura pronta para funcionalidades próprias
└── foundation/
    ├── accounts/       # App compartilhado: usuário, autenticação, perfis e provisionamento
    ├── permissions.py  # Autorização compartilhada (CoupleRequiredMixin)
    ├── templates/      # Base, login e páginas de erro
    └── static/         # CSS compartilhado
```

Os três apps de domínio estão registrados no Django. `couple` e `godparents` ainda não possuem modelos ou rotas próprios; seus campos e operações serão definidos nas próximas etapas. Contas de acesso continuam em `foundation/accounts`, separadas dos registros das listas.

Os labels `accounts` e `guests`, as tabelas e o histórico de migrations foram preservados: a reorganização não exige migração de dados. Imports Python usam `foundation.accounts` e `core.guests`.

Dockerfile, Compose, dependências e scripts de infraestrutura permanecem na raiz. O container executa em `/app/src`, portanto os comandos Docker com `python manage.py` continuam válidos. Fora do container, use `python src/manage.py` a partir da raiz; o módulo de configuração é `config.settings` e o WSGI é `config.wsgi.application`. Para descobrir toda a suíte a partir da raiz, use `python src/manage.py test src`; no container, `python manage.py test` já parte de `src`.

Visitantes são redirecionados ao login. Contas autenticadas de outros perfis recebem HTTP 403 em todas as operações, mesmo se forem superusuários. Apenas contas ativas com perfil Noivos e vaga 1 ou 2 têm acesso. Não há painel administrativo exposto nesta etapa.

Migrations versionadas criam o esquema; não criam contas nem dados de demonstração. As orientações de contribuição estão em [AGENTS.md](AGENTS.md).

## GitHub Actions

Pushes e pull requests para `main` executam os testes no MySQL. Depois de um push aprovado pelos testes, um workflow reutilizável pode atualizar a VPS por SSH. O deploy permanece desabilitado até configurarmos o servidor e `DEPLOY_ENABLED=true` no GitHub.

O gatilho, o job reutilizável e o script da VPS estão separados. Consulte [docs/deployment.md](docs/deployment.md) para os secrets, variáveis e a preparação de produção ainda pendente.
