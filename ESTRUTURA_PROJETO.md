# Documentação da Estrutura do Projeto

Este documento descreve a estrutura de pastas e arquivos do projeto, com uma breve explicação de cada item.

---

## Raiz do Projeto

- **manage.py**: Utilitário principal do Django para comandos administrativos.
- **requirements.txt**: Lista de dependências Python do projeto.
- **db.sqlite3**: Banco de dados SQLite utilizado em desenvolvimento.
- **dockerfile**: Script para criação da imagem Docker do projeto.
- **entrypoint.sh**: Script de inicialização para containers Docker.
- **cloudbuild.yaml**: Configuração de build para integração contínua (Google Cloud Build).
- **fase_1.md, fase_2.md, planejamento.md, sync_prompt.md**: Documentação e planejamento do projeto.

---

## Diretórios Principais

### 1. `gestor_financeiro/` (Configuração do Projeto Django)
- **__init__.py**: Indica que o diretório é um pacote Python.
- **settings.py**: Configurações principais do Django.
- **settings_local.py**: Configurações locais (ex: desenvolvimento).
- **urls.py**: Rotas globais do projeto.
- **wsgi.py**: Interface para servidores WSGI.
- **asgi.py**: Interface para servidores ASGI.

### 2. `core/` (Aplicação Principal)
- **__init__.py**: Indica que o diretório é um pacote Python.
- **admin.py**: Configuração do Django Admin para os modelos da aplicação.
- **apps.py**: Configuração da aplicação Django.
- **context_processors.py**: Funções para adicionar variáveis globais aos templates.
- **forms.py**: Formulários Django utilizados na aplicação.
- **models.py**: Definição dos modelos (tabelas do banco de dados).
- **signals.py**: Sinais do Django para executar ações automáticas.
- **tests.py**: Testes automatizados da aplicação.
- **urls.py**: Rotas específicas da aplicação `core`.
- **utils.py**: Funções utilitárias auxiliares.

#### Subpastas de `core/`

- **migrations/**: Arquivos de migração do banco de dados.
  - **0001_initial.py, ...**: Scripts de criação e alteração de tabelas.
  - **__init__.py**: Indica que é um pacote Python.

- **services/**: Lógica de negócio separada por domínio.
  - **account_service.py**: Serviços relacionados a contas.
  - **csv_import_service.py**: Importação de dados via CSV.
  - **dashboard_service.py**: Lógica do dashboard.
  - **fatura_service.py**: Serviços de faturas.
  - **lancamento_service.py**: Serviços de lançamentos financeiros.
  - **ofx_import_service.py**: Importação de arquivos OFX.
  - **report_service.py**: Geração de relatórios.
  - **rule_service.py**: Regras de categorização e automação.
  - **__init__.py**: Pacote Python.

- **templatetags/**: Filtros e tags customizadas para templates Django.
  - **formatacao.py**: Filtros de formatação.
  - **widget_tweaks.py**: Customização de widgets de formulário.
  - **__init__.py**: Pacote Python.

- **views/**: Views organizadas por domínio.
  - **auth_views.py**: Autenticação e login.
  - **cartao_views.py**: Cartões de crédito.
  - **categoria_views.py**: Categorias de despesas/receitas.
  - **conta_views.py**: Contas bancárias.
  - **dashboard_views.py**: Dashboard principal.
  - **fatura_views.py**: Faturas de cartão.
  - **import_views.py**: Importação de dados.
  - **lancamento_views.py**: Lançamentos financeiros.
  - **regra_views.py**: Regras de automação.
  - **report_views.py**: Relatórios.
  - **__init__.py**: Pacote Python.

### 3. `templates/` (Templates HTML)
- **base.html**: Template base para herança.
- **core/**: Templates específicos da aplicação principal (ex: `cartao_credito_list.html`, `categoria_form.html`, etc).
- **registration/**: Templates para autenticação e cadastro de usuários.

### 4. `static/` (Arquivos Estáticos)
- **js/**: Scripts JavaScript.
  - **components/**: Componentes JS reutilizáveis.
  - **pages/**: Scripts específicos de páginas.

---