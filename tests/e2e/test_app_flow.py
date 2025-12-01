import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
def test_main_flow(page: Page):
    """
    Testa o fluxo principal: carregar a página, criar uma tarefa e verificar o resultado.
    """
    # 1. Navegar para a página
    # Assumindo que o ambiente de teste sobe na porta 8001
    page.goto("http://localhost:8001/dashboard")

    # 2. Verificar se o título da página está correto
    expect(page).to_have_title("DevAgentAtomic Dashboard")

    # 3. Encontrar o campo de texto e o botão
    # Ajustado para o fluxo implementado: Botão "Plan / Audit" -> Modal

    # Verifica se o botão principal existe
    plan_button = page.get_by_role("button", name="Plan / Audit")
    expect(plan_button).to_be_visible()

    # Clica para abrir modal (para verificar inputs)
    plan_button.click()

    task_input = page.get_by_placeholder("Ex: Implement game over logic...")
    submit_button = page.get_by_role("button", name="Generate Plan")

    # Verificar se os elementos estão visíveis
    expect(task_input).to_be_visible()
    expect(submit_button).to_be_visible()

    # TODO: A implementação do resto do teste (clicar, verificar resultado)
    # será feita após resolvermos o problema do ambiente.
