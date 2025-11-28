# DevAgentAtomic 🚀

Sistema de agentes autônomos para desenvolvimento de software "High-End", focado em TDD, Passos Atômicos, Self-Healing e Code Review.

## Funcionalidades Principais

*   **Agentes Autônomos:**
    *   **Tech Lead:** Planeja a arquitetura e divide tarefas.
    *   **Fullstack:** Escreve testes (TDD), implementa código e corrige erros (Self-Healing).
    *   **Reviewer:** Analisa a qualidade e segurança do código gerado.
*   **Execução Segura:** Todo código gerado roda em um ambiente Docker isolado.
*   **Memória (RAG):** Utiliza banco vetorial (pgvector) para contexto do projeto.
*   **Dashboard:** Interface web para monitoramento em tempo real.

## Stack

*   **Backend:** Python 3.11, FastAPI, Celery, SQLAlchemy.
*   **Infra:** Docker, PostgreSQL (pgvector), Redis.
*   **AI:** LangChain (Google Gemini, OpenAI, Anthropic).

## Como Rodar

1.  **Configuração:**
    ```bash
    cp .env.example .env
    # Edite .env com suas chaves de API e defina HOST_WORKSPACE_PATH
    ```

2.  **Instalação:**
    ```bash
    poetry install
    ```

3.  **Infraestrutura:**
    ```bash
    make up  # ou: docker-compose -f infra/docker-compose.yml up -d
    ```

4.  **Execução:**
    *   Terminal 1 (Worker): `make worker`
    *   Terminal 2 (API): `make api`

5.  **Acesso:**
    *   Dashboard: [http://localhost:8001/dashboard/index.html](http://localhost:8001/dashboard/index.html)
