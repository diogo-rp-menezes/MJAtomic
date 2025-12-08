from src.core.models import Step, TaskStatus
from src.core.interfaces import ILLMProvider
from src.core.logger import logger
from src.agents.fullstack.components import PromptBuilder, ResponseHandler
import json
from typing import Tuple, List

class FullstackAgent:
    def __init__(self,
                 llm: ILLMProvider,
                 prompt_builder: PromptBuilder,
                 response_handler: ResponseHandler,
                 workspace_path: str = "./workspace"):

        self.workspace_path = workspace_path
        self.llm = llm
        self.prompt_builder = prompt_builder
        self.response_handler = response_handler

    def execute_step(self, step: Step, task_input: str = None) -> Tuple[Step, List[str]]:
        logger.info(f"🤖 [Fullstack] Executing: {step.description}")
        step.status = TaskStatus.IN_PROGRESS

        system_prompt = self.prompt_builder.build_system_prompt()
        history = ""
        attempts = 0
        max_attempts = 5
        modified_files = []

        while attempts < max_attempts:
            attempts += 1

            # 1. Build Context
            context = self.prompt_builder.build_context(step, history, task_input)

            # 2. Call LLM
            response = self.llm.generate_response(
                prompt=context,
                system_message=system_prompt,
                schema=None
            )
            logger.debug(f"Resposta bruta do LLM: {response}")

            try:
                # 3. Clean and Parse JSON
                clean_json = response.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                logger.debug(f"JSON decodificado: {data}")

                # 4. Handle Response (Side Effects & Command Execution)
                output_log, current_files, success = self.response_handler.handle(data)

                if success:
                    step.status = TaskStatus.COMPLETED
                    step.result = f"Success! Output: {output_log[:500]}..."
                    step.logs = history + "\n" + output_log
                    return step, current_files
                else:
                    # Self-Healing
                    history += f"\n\nATTEMPT {attempts} FAILED:\nOutput: {output_log}\n\nFix the code and try again."
                    logger.info(f"Self-healing attempt {attempts}...")
                    modified_files = current_files # Keep track

            except json.JSONDecodeError as e:
                logger.error(f"Erro de decodificação JSON: {e}")
                history += "\n\nERROR: Invalid JSON response. Please format as valid JSON."
            except Exception as e:
                logger.error(f"Erro inesperado no loop: {e}")
                history += f"\n\nERROR: {str(e)}"

        step.status = TaskStatus.FAILED
        step.logs = history
        step.result = "Failed after max attempts."
        return step, modified_files
