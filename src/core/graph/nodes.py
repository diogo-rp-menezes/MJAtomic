from src.agents import (ArchitectAgent, DevOpsAgent, FullstackAgent,
                         ReviewerAgent, TechLeadAgent)
from src.core.agents.state import AgentState


def planning_node(state: AgentState):
    """
    Node for the planning phase, involving the TechLead and Architect.
    """
    tech_lead = TechLeadAgent()
    architect = ArchitectAgent()

    plan = tech_lead.create_development_plan(
        state["project_name"], state.get("language", "python")
    )
    structure = architect.execute(state["project_name"])

    return {
        "plan": plan.dict(),
        "structure": structure,
        "current_step_index": 0,
    }


def code_execution_node(state: AgentState):
    """
    Node for executing a single step of the development plan.
    """
    fullstack_agent = FullstackAgent()
    step = state["plan"]["steps"][state["current_step_index"]]

    code_execution = fullstack_agent.execute_task(step)
    test_results = fullstack_agent.run_tests(step["test_command"])

    return {
        "code": code_execution.code,
        "test_results": test_results.dict(),
    }


def review_node(state: AgentState):
    """
    Node for reviewing the code generated in the execution phase.
    """
    reviewer_agent = ReviewerAgent()
    step = state["plan"]["steps"][state["current_step_index"]]

    review = reviewer_agent.review_code(step, state["code"])

    return {"review": review.dict()}


def self_healing_node(state: AgentState):
    """
    Node for attempting to self-heal the code based on review feedback.
    """
    fullstack_agent = FullstackAgent()
    step = state["plan"]["steps"][state["current_step_index"]]

    fixed_code_result = fullstack_agent.fix_code(
        step, state["code"], state["test_results"]
    )

    return {
        "code": fixed_code_result.code_execution.code,
        "test_results": fixed_code_result.test_result.dict(),
        "review": {"status": fixed_code_result.status},
    }


def human_in_loop_node(state: AgentState):
    """
    Node for pausing the process and waiting for human feedback.
    """
    # This node will typically involve an external trigger (e.g., API call)
    # to provide feedback. For now, we'll just set the flag.
    return {"is_human_in_loop": True}
