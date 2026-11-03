# Wedding

Wedding é uma aplicação pessoal para apoiar o planejamento do casamento do autor com sua noiva. O projeto é voltado a um único casamento.

## Estado atual

O projeto está na fase de planejamento inicial. Ainda não há funcionalidades, aplicação ou infraestrutura implementadas neste repositório.

## Perfis previstos

- **Noivos:** foco da primeira etapa, com acesso às ferramentas de planejamento.
- **Convidados:** perfil previsto, com funcionalidades a definir posteriormente.
- **Padrinhos:** perfil previsto, com funcionalidades a definir posteriormente.

## Escopo inicial

A primeira etapa de implementação será dedicada à visão dos noivos, começando por:

- Lista de convidados.
- Lista de padrinhos.

As duas listas estarão disponíveis exclusivamente para os noivos. Essa restrição deverá ser aplicada no backend Django e refletida na interface.

Cadastrar alguém em uma lista não implica criar uma conta de acesso. A relação entre os registros das listas e os perfis de acesso será definida posteriormente.

## Arquitetura prevista

- **Django:** framework da aplicação.
- **MySQL:** banco de dados principal.
- **Docker:** execução da aplicação e do banco em serviços separados.
- **Docker Compose:** orquestração dos serviços no ambiente local e na futura implantação.
- **VPS da Hostinger:** destino previsto para hospedagem.

As configurações serão fornecidas por variáveis de ambiente, sem credenciais versionadas. A persistência utilizará migrations do Django e armazenamento persistente para o MySQL.

Versões das dependências, autenticação e detalhes de implantação ainda serão definidos. Instruções de instalação e execução serão adicionadas quando a configuração correspondente existir.

## Próximas etapas

1. Detalhar os fluxos de planejamento da visão dos noivos.
2. Definir os dados e as operações das listas de convidados e padrinhos.
3. Planejar a autenticação e as regras de autorização.
4. Preparar a estrutura técnica com Django, MySQL e Docker Compose.
5. Implementar as listas e testar as restrições de acesso.

## Orientações para contribuição

As orientações para agentes que trabalharem no projeto estão em [AGENTS.md](AGENTS.md).
