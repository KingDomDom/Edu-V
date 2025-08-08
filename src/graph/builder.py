from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .types import State
from .nodes import (
    coordinator_node,
    teach_planner_node,
    study_planner_node,
)

def _build_base_graph():
    builder = StateGraph(State)
    builder.add_edge(START, "coordinator")
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("teach_planner", teach_planner_node)
    builder.add_node("study_planner", study_planner_node)
    builder.add_edge("teach_planner", END)
    builder.add_edge("study_planner", END)
    
    return builder

def build_graph_with_memory():
    memory = MemorySaver()
    
    builder = _build_base_graph()
    return builder.compile(checkpointer=memory)

def build_graph():
    builder = _build_base_graph()
    return builder.compile()

graph = build_graph()