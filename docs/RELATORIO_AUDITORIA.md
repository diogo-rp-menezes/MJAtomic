# Relatório de Auditoria Arquitetural e Plano de Refatoração
**Projeto:** DevAgentAtomic
**Versão Auditada:** Atual (src/)
**Data:** 08/12/2024
**Auditor:** Arquiteto Sênior (Jules)

---

## 1. Diagnóstico Executivo

**Nota de Adesão:** ⭐ **6.5 / 10**

O projeto demonstra uma estrutura organizada e o uso de tecnologias modernas (FastAPI, LangGraph, Pydantic), porém falha em separar claramente as responsabilidades entre a Lógica de Orquestração (Agentes) e a Infraestrutura (Ferramentas/IO). O código é funcional, mas apresenta alto acoplamento, dificultando testes unitários isolados e evoluções futuras (como trocar o executor de comandos ou o provedor de LLM sem reescrever os agentes).

### Principais Riscos (Top 3)

1.  **Acoplamento Rígido (Violação DIP/Hexagonal):**
    *   Agentes instanciam ferramentas (`SecureExecutorTool`, `FileIOTool`) e classes de infraestrutura (`LLMProvider`) diretamente ou via valores default nos construtores. Isso impede o mock fácil para testes e amarra o domínio à implementação concreta.
2.  **Violação de Responsabilidade Única (SRP - God Classes):**
    *   A classe `FullstackAgent` acumula responsabilidades de: Orquestração do fluxo, Engenharia de Prompt, Parsing de JSON, Parsing de Comandos de Shell (`BG_START`), Manipulação de Arquivos e Lógica de Retry/Self-Healing.
3.  **Fragilidade a Mudanças (Violação OCP):**
    *   A classe `LLMProvider` usa condicionais explícitas (`if provider == "google"`, `elif "local"`) para instanciar clientes. Adicionar um novo provedor exige modificar a classe central, arriscando quebrar o que já funciona.

---

## 2. Análise de Violações

| Arquivo / Componente | Violação (Manual/Princípio) | Trecho Problemático (Resumo) | Correção Sugerida |
| :--- | :--- | :--- | :--- |
| `src/agents/fullstack/agent.py` | **SRP (Single Responsibility)** | Método `execute_step` possui ~80 linhas e gerencia Prompt, IO, Parsing e Retry. | Extrair `PromptBuilder`, `CommandParser` e `ExecutionStrategy`. O Agente deve apenas orquestrar. |
| `src/agents/fullstack/agent.py` | **DIP (Dependency Inversion)** | `self.file_io = file_io or FileIOTool(...)` (Instanciação concreta no default). | Remover defaults concretos. Injetar interfaces (`IFileSystem`, `IExecutor`) via construtor ou container de DI. |
| `src/agents/fullstack/agent.py` | **Clean Code (Complexidade)** | Lógica de `if cmd.startswith("BG_START:")` encadeada (Switch manual). | Usar padrão **Command** ou **Strategy** para tratar diferentes tipos de ações do agente. |
| `src/core/llm/provider.py` | **OCP (Open/Closed)** | `_create_llm_instance` com `if/elif` para cada provedor. | Usar padrão **Factory** com registro dinâmico de provedores ou Polimorfismo. |
| `src/core/llm/provider.py` | **SRP / Clean Code** | `generate_response` mistura lógica de retry, fallback (Plan A/B/C) e chamada de API. | Mover lógica de Fallback/Retry para um **Decorator** ou **Policy** separada. |
| `src/agents/tech_lead/agent.py` | **Clean Code (Hardcoding)** | Path do prompt hardcoded: `_load_prompt_template("src/agents/tech_lead_prompt.md")`. | Mover configurações de caminhos para `Settings` ou injetar via configuração. |

---

## 3. Plano de Refatoração

Para mitigar os riscos sem paralisar o desenvolvimento, propõe-se uma abordagem em 3 fases:

### Fase 1: Estrutural (Arquitetura e Desacoplamento)
*Objetivo: Permitir testes unitários reais e isolar o domínio.*

1.  **Definir Interfaces (Protocolos):** Criar `src/core/interfaces.py` definindo `LLMClient`, `CommandExecutor`, `FileSystem`.
2.  **Injeção de Dependência:** Refatorar construtores de `TechLeadAgent` e `FullstackAgent` para receberem **apenas** interfaces. Remover instanciação direta de `SecureExecutorTool` e `LLMProvider` dentro das classes.
3.  **Factory de Agentes:** Criar `AgentFactory` em `src/core/factory.py` para centralizar a "montagem" dos agentes com suas dependências concretas (wiring).

### Fase 2: Limpeza (Clean Code e Patterns)
*Objetivo: Reduzir complexidade ciclomática e facilitar leitura.*

1.  **Refatorar `FullstackAgent`:**
    *   Extrair lógica de parser de comandos para `CommandParser`.
    *   Extrair lógica de retry/loop para um método ou classe base `ResilientAgent`.
2.  **Refatorar `LLMProvider`:**
    *   Transformar em uma fachada simples que delega para implementações de `LLMClient` (GoogleClient, LocalClient) que herdam de uma base comum.
3.  **Padronização PEP 8:** Garantir que todas as funções usem `snake_case` (já verificado como aderente, mas manter vigilância).

### Fase 3: Blindagem (Testes e Segurança)
*Objetivo: Garantir estabilidade.*

1.  **Testes Unitários Isolados:** Criar testes para `FullstackAgent` usando **Mocks** para o `executor` e `llm`. Hoje os testes provavelmente dependem de IO real ou são de integração.
2.  **Validação Estrita:** Melhorar a validação dos DTOs de entrada e saída dos agentes.

---

## 4. Exemplo de Refatoração "Antes vs Depois"

**Foco:** `src/agents/fullstack/agent.py` (Classe `FullstackAgent`)

### ANTES (O "Smell")
*Acoplado, mistura responsabilidades, difícil de testar.*

```python
# src/agents/fullstack/agent.py (Resumo do atual)
class FullstackAgent:
    def __init__(self, workspace_path="./workspace", ...):
        # Acoplamento direto com implementações concretas
        self.executor = SecureExecutorTool(workspace_path)
        self.llm = LLMProvider(model_name=...)

    def execute_step(self, step):
        # Mistura construção de prompt, loop de retry e execução
        system_prompt = "You are an Expert..."
        while attempts < 5:
            response = self.llm.generate_response(...)
            data = json.loads(response) # Parsing manual frágil

            if data["command"].startswith("BG_START"):
                 # Lógica de execução misturada com orquestração
                 self.executor.start_background_process(...)
            # ... mais 50 linhas de if/else
```

### DEPOIS (Clean Architecture & SOLID)
*Desacoplado, Testável, SRP respeitado.*

```python
# src/agents/fullstack/agent_refactored.py

from typing import Protocol, List
from src.core.models import Step, TaskStatus
from src.core.interfaces import ILExecutor, ILLMClient, IFileSystem

# 1. Interface para o Executor (Inversão de Dependência)
class IAgentExecutor(Protocol):
    def execute_command(self, command: str) -> str: ...

# 2. Strategy para lidar com respostas do LLM
class AgentResponseHandler:
    def __init__(self, file_system: IFileSystem, executor: IAgentExecutor):
        self.fs = file_system
        self.executor = executor

    def handle_response(self, structured_response: dict) -> str:
        # Responsabilidade Única: Executar o que o LLM pediu
        self.fs.write_files(structured_response.get("files", []))
        cmd = structured_response.get("command")
        if cmd:
            return self.executor.execute_command(cmd)
        return "No command executed."

# 3. O Agente (Apenas Orquestra)
class FullstackAgent:
    def __init__(
        self,
        llm: ILLMClient,
        handler: AgentResponseHandler,
        system_prompt: str
    ):
        # Depende apenas de abstrações injetadas
        self.llm = llm
        self.handler = handler
        self.system_prompt = system_prompt

    def execute_step(self, step: Step) -> Step:
        # Foco puramente no fluxo (Loop TDD / Self-Healing)
        context = self._build_context(step)

        for attempt in range(3):
            try:
                response = self.llm.generate_structured(
                    prompt=context,
                    system=self.system_prompt
                )

                result_log = self.handler.handle_response(response)

                step.status = TaskStatus.COMPLETED
                step.result = result_log
                return step

            except Exception as e:
                context += f"\nError: {str(e)}. Try again."

        step.status = TaskStatus.FAILED
        return step

    def _build_context(self, step: Step) -> str:
        # Lógica de montagem de contexto isolada
        return f"Task: {step.description}..."
```

**Ganhos Imediatos:**
1.  **Testabilidade:** Podemos testar `execute_step` passando um `MockLLM` e um `MockHandler`, sem rodar Docker nem escrever arquivos reais.
2.  **Manutenibilidade:** Se quisermos mudar como o `BG_START` funciona, alteramos apenas o `AgentResponseHandler` (ou a implementação concreta do `executor`), sem tocar na lógica do Agente.
3.  **Clareza:** O método `execute_step` descreve *o que* o agente faz (tenta, executa, corrige), não *como* ele faz (parse string, abre arquivo, chama subprocess).
