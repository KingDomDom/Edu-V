import logging
import os
from dataclasses import dataclass, field, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig

from src.rag.retriever import Resource

logger = logging.getLogger(__name__)

def get_recursion_limit(default: int = 25) -> int:
    try:
        env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default))
        parsed_limit = int(env_value_str)
        
        if parsed_limit > 0:
            logger.info(f"Recursion limit set to: {parsed_limit}")
            return parsed_limit
        else:
            logger.warning(
                f"AGENT_RECURSION_LIMIT value '{env_value_str}' (parsed ad {parsed_limit}) is not positive"
                f"Using default value {default}"    
            )
            return default
    except ValueError:
        raw_env_value = os.getenv("AGENT_RECURSION_LIMIT")
        logger.warning(
            f"Invalid AGENT_RECURSION_LIMIT value: '{raw_env_value}'"
            f"Using default value {default}"
        )
        return default
    
@dataclass(kw_only=True)
class Configuration:
    resources: list[Resource] = field(
        default_factory=list
    )
    max_plan_iterations: int = 1
    max_step_num: int = 3
    max_search_results: int = 3
    mcp_settings: dict = None
    enable_deep_thinking: bool = False
    
    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    )-> "Configuration":
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(),configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})
    