from typing import Literal

LLMType = Literal["basic", "reasoning", "vision"]

AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "basic",
    "teach_planner": "basic",
    "study_planner": "basic",
    "online_investigator": "basic",
}