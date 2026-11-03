# Orientações para agentes

Estas orientações se aplicam a todo o repositório Wedding.

## Contexto e prioridades

- Preserve o propósito de aplicação pessoal para apoiar o planejamento de um único casamento, do autor com sua noiva.
- Considere os três perfis previstos: Noivos, Convidados e Padrinhos.
- Priorize a visão dos noivos, começando pela lista de convidados e pela lista de padrinhos.
- Não implemente funcionalidades exclusivas de Convidados ou Padrinhos sem uma definição posterior de escopo.

## Acesso e registros

- Restrinja as duas listas exclusivamente aos noivos.
- Aplique a autorização no backend Django; ocultar elementos da interface não substitui a verificação de acesso no servidor.
- Reflita as permissões na interface.
- Não presuma que cadastrar um convidado ou padrinho cria uma conta de acesso. A relação entre registros das listas e contas será definida posteriormente.
- Ao implementar essas funcionalidades, teste o acesso permitido aos noivos e a rejeição de acessos sem autenticação ou com outros perfis.

## Diretrizes técnicas

- Use Django para a aplicação e MySQL como banco de dados principal.
- Mantenha a aplicação e o banco em serviços Docker separados.
- Adote Docker Compose para a orquestração local e para a futura implantação na VPS da Hostinger.
- Forneça configurações por variáveis de ambiente e não versione credenciais ou segredos.
- Ao implementar persistência, use migrations do Django para alterações de esquema e armazenamento persistente para o MySQL.

## Evolução do projeto

- O estado inicial contém apenas documentação: funcionalidades e infraestrutura ainda são planejadas.
- Mantenha o README.md atualizado conforme a implementação evoluir, distinguindo o que está planejado do que já existe.
- Só documente comandos de instalação e execução quando a configuração correspondente estiver disponível.
- Defina versões de dependências, autenticação, campos e operações das listas e detalhes de implantação nas respectivas etapas de planejamento.
- Valide as mudanças com verificações adequadas ao escopo; para funcionalidades com controle de acesso, inclua testes das regras de autorização.
