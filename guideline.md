# Guideline: Reconstruindo o DevAgentAtomic

Este documento serve como referência para recriar o projeto DevAgentAtomic. Ele captura as principais decisões de arquitetura, detalhes de implementação e procedimentos operacionais com base no ambiente anterior.

## 1. Visão Geral e Objetivos do Projeto

-   **Nome do Projeto:** DevAgentAtomic
-   **Conceito Principal:** Um sistema de agente de desenvolvimento de software autônomo focado em Desenvolvimento Guiado por Testes (TDD) e na execução de tarefas em etapas atômicas e verificáveis.
-   **Status:** O projeto é um MVP funcional com recursos avançados, incluindo Persistência, RAG, Auto-Correção e um Dashboard. O plano 'Fortalecimento do DevAgentAtomic', que estabeleceu uma rede de segurança de testes robusta, foi concluído.
-   **Branch Principal:** `main` é o branch de integração primário.

## 2. Arquitetura e Componentes Principais

-   **Arquitetura Geral:** O sistema consiste em um API Gateway FastAPI, um dashboard Frontend em Vue.js e um conjunto de agentes orquestrados por LangGraph, processados por workers Celery.
-   **Frontend:**
    -   Um dashboard estático em HTML/Vue.js estilizado com Tailwind CSS.
    -   Servido pelo FastAPI no endpoint `/dashboard`.
    -   Funcionalidades incluem criação de tarefas, listagem de histórico e monitoramento em tempo real.
    -   Inclui uma UI de "Modo Interativo" com um botão de continuar e entrada de feedback para suportar fluxos de trabalho com intervenção humana (Human-in-the-Loop - HITL).
-   **Backend (API & Worker):**
    -   **API Gateway:** Aplicação FastAPI. Suporta `POST /resume/{plan_id}` para interagir com threads do grafo pausadas para HITL.
    -   **Processamento de Tarefas:** Workers Celery executam o fluxo de trabalho do agente usando as tarefas `run_agent_graph` e `resume_agent_graph`.
-   **Orquestração (LangGraph):**
    -   O fluxo de trabalho principal é uma máquina de estados baseada em LangGraph (`src/core/graph`).
    -   Isso permite fluxos de trabalho não lineares, novas tentativas (loops), arestas condicionais e persistência de estado (checkpointing).
    -   A função `create_dev_graph_with_checkpoint` em `src/core/graph/workflow.py` é um ponto de entrada chave, usado pelo worker Celery.
-   **Agentes (`src/agents/`):**
    -   O sistema usa um enum `AgentRole` que inclui `TECH_LEAD`, `FULLSTACK`, `DEVOPS`, `REVIEWER` e `ARCHITECT`.
    -   Cada agente tem uma responsabilidade específica dentro do ciclo de vida do desenvolvimento.

## 3. Persistência de Estado e Dados

-   **Banco de Dados:** PostgreSQL é usado para dados relacionais, `pgvector` para embeddings e para armazenar checkpoints do LangGraph.
-   **ORM:** A persistência de estado usa o SQLAlchemy ORM.
-   **Tabelas:**
    -   `development_plans` e `steps` para rastreamento de tarefas.
    -   `graph_checkpoints` para o estado do LangGraph.
-   **Persistência do LangGraph:** Um `PostgresSaver` personalizado em `src/core/graph/checkpoint.py` lida com o salvamento do estado do grafo no modelo `DBCheckpoint`.

## 4. Infraestrutura e Dependências

-   **Ambiente de Execução:** Todo o ambiente é orquestrado através de um arquivo `docker-compose.yml` na raiz (API, Worker, Postgres, Redis).
-   **Serviços Principais:** Requer Redis (broker/backend do Celery), Postgres e Docker.
-   **Python:** O projeto usa Python 3.12+ e gerencia dependências com Poetry.
-   **Provedores de LLM:**
    -   Suporta os provedores OpenAI, Anthropic e Google LLMs, configuráveis através da variável de ambiente `LLM_PROVIDER`.
    -   O usuário utiliza exclusivamente a API do Google (Gemini).
-   **Bibliotecas Chave:**
    -   Ecossistema `langchain` (ex: `langchain` 0.3.18, `langchain-core` 0.3.36).
    -   `langgraph` para orquestração.
    -   `playwright` e `pytest-playwright` para testes E2E.

## 5. Estratégia de Desenvolvimento e Testes

-   **CI/CD:** A Integração Contínua é configurada usando GitHub Actions (`.github/workflows/ci.yml`). O pipeline instala os navegadores do Playwright (`poetry run playwright install chromium`) e executa os testes (`poetry run pytest`) em Python 3.10.
-   **Framework de Testes:** `pytest` é o executor de testes principal.
-   **Organização dos Testes:**
    -   **Testes Unitários (`tests/unit/`):** Arquivos dedicados para cada agente (`test_fullstack_agent.py`, `test_tech_lead_agent.py`, etc.) e para a lógica do grafo.
    -   **Testes de Integração (`tests/integration/`):** Inclui `tests/test_integration.py` para a cadeia completa de agentes (usando mocks) e `tests/integration/test_worker_graph.py` para a camada Celery/LangGraph.
    -   **Testes E2E (`tests/e2e/`):** Implementados com Playwright. `test_frontend.py` verifica a UI geral, e `test_hitl.py` verifica as funcionalidades de HITL. Os testes E2E executam um servidor HTTP local para o frontend estático para evitar problemas com `file://`.
-   **Configuração de E2E:** O comando `poetry run playwright install chromium` deve ser executado em qualquer novo ambiente para habilitar os testes E2E.

## 6. Detalhes de Implementação Específicos dos Agentes

#### TechLeadAgent
-   Usa um método `_parse_with_retry` para extrair de forma confiável um objeto ou lista JSON da resposta do LLM, limpando a formatação markdown.

#### ArchitectAgent (`src/agents/architect`)
-   Refinado para uma inicialização de projeto robusta, com sua funcionalidade verificada por testes unitários.

#### DevOpsAgent (`src/agents/devops`)
-   Automatiza tarefas de infraestrutura (ex: Dockerfiles, pipelines de CI).
-   Usa o perfil `smart` do LLM e a `SecureExecutorTool`.

#### FullstackAgent
-   **Configuração:** Configurado através de um arquivo `config.yaml` externo para mapear linguagens a comandos de teste.
-   **Lógica TDD:** Considera uma falha de teste (código de saída != 0) como uma etapa `COMPLETED` durante a fase "VERMELHA" do TDD.
-   **Auto-Correção:** Implementa um mecanismo de nova tentativa (até 3 vezes) que alimenta os logs de execução de tentativas falhas de volta ao LLM para corrigir erros.
-   **Execução de Código:** Usa uma `SecureExecutorTool` para executar código em contêineres Docker sandbox. Monta o volume do workspace local e executa como root (`user 0`) para garantir permissões de arquivo.
-   **RAG (Geração Aumentada por Recuperação):**
    -   Usa um `CodeIndexer` com `RecursiveCharacterTextSplitter` para indexar o workspace.
    -   Recupera contexto para aumentar os prompts para geração de código.
    -   Usa `pgvector` para armazenar embeddings de código, com dimensões dinâmicas baseadas no provedor de LLM (768 para Google, 1536 para OpenAI).
    -   Lida com erros de inicialização em `VectorMemory` ou `CodeIndexer` de forma graciosa, registrando a falha e operando em um modo degradado sem RAG.
-   **Análise de Saída:** Impõe uma saída JSON estrita do LLM e usa `json.loads` para uma análise confiável.

#### CodeReviewAgent
-   Analisa as alterações de código em busca de segurança, estilo e desempenho. Uma etapa só é marcada como `COMPLETED` se a revisão for aprovada.
