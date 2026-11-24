# Produção na Hostinger

O Wedding roda em produção na VPS 1625057 e atende `dudaejose.com.br`, `www.dudaejose.com.br` e `wedding.srv1625057.hstgr.cloud`. O banco local é independente do banco `wedding_producao` e recebe as mesmas migrations.

Importe compose.vps.yaml de uma revisão Git publicada e fixe APP_REF nessa revisão. Configure no painel DJANGO_SECRET_KEY (aleatório, 64 bytes), MYSQL_USER, MYSQL_PASSWORD e MYSQL_ROOT_PASSWORD. Não reutilize segredos antigos. A rede shared_net deve existir e ser alcançável pelo Traefik em rede host.

Antes da primeira implantação: validar imagem local, conferir os recursos do projeto wedding e remover exclusivamente sua implantação antiga e volume wedding_mysql_data, conforme exclusão autorizada. Não remover outros projetos.

No diretório do projeto no servidor, com as variáveis configuradas:

```sh
docker compose build web
docker compose up -d db
docker compose run --rm web python manage.py check --deploy --fail-level WARNING
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py createsuperuser
docker compose up -d web
```

O painel pode não executar build: nesse caso, usar os comandos acima por SSH. Não iniciar web antes das migrations. Verificar certificado, redirecionamento HTTP, login/logout, CSS do Admin e /health/. O health retorna 503 se o banco falhar. O endpoint deve ser usado para monitoramento externo.

HSTS inicial de 3600 segundos; os avisos de preload e inclusão de subdomínios são silenciados especificamente, por decisão explícita. Não há serviço init permanente.

### Redefinição de senha

Os noivos encontram os pedidos em **Gerenciar participantes → Pedidos de redefinição de senha**. Após confirmar a identidade por um contato conhecido, devem compartilhar o link em particular. O link vale por 24 horas e só pode ser usado uma vez. Não há envio automático por e-mail.

Trate logs de acesso como dados restritos: a rota inicial `/password-reset/<id>/link/<token>/` contém a credencial de redefinição, assim como os links de ativação. O formulário é aberto em uma segunda URL, sem o token. Os limites de tentativa usam o cache local do Django, compatível com o único worker atual do Gunicorn; ao ampliar o número de workers ou réplicas, configure um cache compartilhado que ofereça incremento atômico.

Antes de atualizações, salvar dump do MySQL e revisão da imagem. Reverter imagem não desfaz migrations: restaurar backup se a alteração de esquema for incompatível. Nunca remover wedding_producao_mysql_data durante atualizações.

## Estado da primeira implantação

A primeira versão foi transferida por SSH para /docker/wedding-release e construída como wedding-base:release, pois a revisão ainda não foi publicada no Git. O Compose operacional está em /docker/wedding/docker-compose.yml, com segredos em /docker/wedding/.env (permissão 600). Não reimporte o YAML remoto antes de publicar os arquivos atualizados e fixar APP_REF.

Para criar a conta administrativa, execute em terminal interativo:

```sh
ssh -t root@177.7.40.156 'cd /docker/wedding && docker compose exec web python manage.py createsuperuser'
```

## Deploy automático da main

O workflow `.github/workflows/main.yml` valida build, migrations, segurança e HTTP com MySQL em cada PR/push. Push na main e execução manual na main implantam a revisão validada por SSH. Deploys não se interrompem entre si.

Cada deploy gera o Compose da VPS a partir de `compose.vps.yaml`. Atualize nesse arquivo a regra do Traefik, os hosts permitidos e as origens CSRF do Django ao adicionar um domínio.

Secrets do GitHub: `VPS_DEPLOY_KEY` (chave exclusiva) e `VPS_KNOWN_HOSTS` (identidade verificada do servidor). A chave usa comando forçado `/usr/local/sbin/wedding-deploy`, sem shell interativo ou encaminhamento de portas. O script confiável é instalado separadamente; mudanças em `scripts/deploy-vps.sh` exigem sua atualização na VPS.

O servidor mantém releases em `/docker/wedding-releases/<SHA>`, backups SQL compactados em `/docker/wedding/backups` e o SHA concluído em `/docker/wedding/deployed-revision`. Não há remoção automática de backups/imagens: revisar espaço periodicamente. O workflow preserva `.env` e volume MySQL e atualiza apenas web, sem recriar o banco.

Antes de migrations, o deploy gera um dump. Se build/check/backup falhar, a aplicação atual continua. Falhas de migration ou saúde encerram o workflow com erro; não há rollback automático de esquema. A configuração anterior fica em `compose.previous.yaml`; restaurá-la exige avaliar compatibilidade com as migrations aplicadas.

### Atualização do usuário padrão para User customizado

O comando `migrate` da aplicação detecta o histórico legado (`admin.0001_initial`
aplicada sem `wedding.0001_initial`) e executa a adoção antes da verificação de
consistência do Django. Assim, o script de deploy já instalado na VPS continua
funcionando: seu backup ocorre antes da adoção. Não é necessário alterar o
comando forçado de SSH. Bancos novos seguem o fluxo normal de migrations.
Para atualizações manuais, faça backup antes de executar `migrate`.
