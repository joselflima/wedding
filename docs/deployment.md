# Deploy automático para a VPS

## Estado

A automação está preparada no repositório. A publicação real permanece desabilitada até configurarmos a VPS, o ambiente `production` no GitHub e a configuração de produção da aplicação. Nenhum servidor foi alterado nesta etapa.

## Fluxo

1. Push para `main` executa `.github/workflows/main.yml`.
2. O job `test` constrói a aplicação, confere migrations e executa os testes no MySQL 8.4 em ambiente descartável.
3. Se os testes passarem e a variável de repositório `DEPLOY_ENABLED` for exatamente `true`, o workflow chama `.github/workflows/deploy-vps.yml`.
4. O workflow reutilizável usa o ambiente `production` e chama `scripts/run-deploy.sh`, responsável pela conexão SSH.
5. Pela conexão, `scripts/deploy-vps.sh` é enviado via stdin e executado na VPS com o SHA do push. Ele atualiza o checkout para esse commit, constrói a aplicação, verifica as configurações de produção, aplica migrations e atualiza os serviços.

Pull requests para `main` executam somente os testes. É possível reexecutar pelo botão **Run workflow** do workflow **Validate and deploy**, selecionando `main`. A verificação completa também ocorre nessa execução manual.

Deploys não interrompem outro deploy em andamento. O GitHub serializa as execuções e a VPS usa `flock`. Um SHA que já não seja a ponta de `main` é ignorado para impedir a publicação de uma versão antiga que estava na fila. Assim, pushes rápidos podem resultar em apenas a versão mais recente publicada.

## Configuração no GitHub

Em **Settings → Secrets and variables → Actions → Variables**, criar a variável de repositório:

| Variável | Valor |
| --- | --- |
| `DEPLOY_ENABLED` | Deixar ausente ou `false` até a VPS estar pronta; depois usar `true`. |

Criar **Settings → Environments → production**, restringir esse ambiente à branch `main` e configurar:

| Tipo | Nome | Conteúdo |
| --- | --- | --- |
| Variable | `VPS_HOST` | IP IPv4 ou hostname da VPS, sem protocolo. |
| Variable | `VPS_USER` | Usuário SSH de deploy. |
| Variable | `VPS_PORT` | Porta SSH; padrão `22`. |
| Variable | `VPS_APP_DIR` | Caminho absoluto do clone na VPS, sem espaços; por exemplo `/srv/wedding`. |
| Secret | `VPS_SSH_KEY` | Chave SSH privada dedicada ao deploy, sem passphrase, cuja pública está autorizada na VPS. |
| Secret | `VPS_KNOWN_HOSTS` | Entrada `known_hosts` da VPS, com fingerprint conferido por canal confiável. Para porta diferente de 22, usar `[host]:porta`. |

A chave deve ser cadastrada diretamente nos secrets, sem aparecer em commits ou no chat. A conexão exige verificação da identidade do servidor; não usa `StrictHostKeyChecking=no` nem confia automaticamente no resultado de `ssh-keyscan`.

Não configurar revisores obrigatórios no ambiente se a intenção for publicar automaticamente, sem uma aprovação manual por push.

## Preparação pendente da VPS

- Linux com Git, Bash, `flock`, Docker e Docker Compose v2 com suporte a `--wait`.
- Usuário de deploy com acesso ao diretório e ao Docker.
- Clone deste repositório em `VPS_APP_DIR`, com `origin` correto. Se o repositório for privado, configurar na VPS uma credencial de leitura do GitHub, independente da chave GitHub Actions → VPS.
- `.env` de produção no servidor, com segredos próprios, `DJANGO_DEBUG=false`, domínio e demais configurações de segurança. Não copiar o `.env` local.
- `compose.production.yaml` no diretório do clone, mantido no servidor e ignorado pelo Git. Prepararemos esse arquivo após conhecer os serviços já existentes na VPS. Ele deverá substituir `runserver` por um servidor de produção, servir arquivos estáticos, integrar HTTPS/proxy, configurar reinício e healthcheck da aplicação. A configuração de produção precisa passar `manage.py check --deploy --fail-level WARNING`.
- Domínio, DNS, HTTPS, backup do MySQL e política de restauração definidos antes da ativação.

O script aborta se faltarem `.env` ou `compose.production.yaml`, ou se houver alterações locais em arquivos versionados. Ele não cria usuários, não troca senhas e não apaga volumes. A configuração atual de desenvolvimento não está pronta para ser exposta na internet; a automação não elimina essa etapa de preparação.

O nome Compose é fixado em `wedding` para manter a identidade do volume. A primeira instalação deve usar esse mesmo nome, evitando subir um banco vazio por acidente ao mudar o nome do projeto.

## Falhas e atualizações

Falhas de testes impedem a chamada do deploy. Erros de SSH, build, verificações, migrations ou inicialização deixam o job vermelho no GitHub. Não há rollback automático do banco: migrations podem ter sido aplicadas antes de uma falha na inicialização. Atualizações de esquema devem ser compatíveis com a versão anterior enquanto ela estiver rodando, e a rotina de backup precisa estar pronta antes de ativar o deploy.

Se uma execução falhar depois de atualizar o checkout, os containers antigos podem continuar ativos; o SHA no diretório sozinho não comprova que a nova versão está servindo. A etapa `up --wait` verifica os serviços; a definição do healthcheck HTTP e a conferência pública de HTTPS serão completadas com a configuração da VPS.

Para desligar somente a publicação automática, definir `DEPLOY_ENABLED=false`. Os testes continuam rodando.
