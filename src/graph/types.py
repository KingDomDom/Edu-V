from langgraph.graph import MessagesState

from src.prompts.planner_model import Plan
from src.rag import Resource

class State(MessagesState):
    locale: str = "zh-CN"
    research_topic: str = ""
    observations: list[str] = []
    resources: list[Resource] = []
    plan_iterations:int = 0
    current_plan: Plan | str = None
    final_report:str = ""
    auto_accepted_plan: bool = False
    enable_online_invest: bool = False
    online_invest_result: str = ""