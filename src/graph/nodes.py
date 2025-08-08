import json
import logging
import os
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import Command, interrupt
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.agents import create_agent
from src.tools.search import LoggedTavilySearch
from src.tools import (
    crawl_tool,
    get_web_search_tool,
    get_retriever_tool,
    python_repl_tool,
)

from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.planner_model import Plan
from src.prompts.template import apply_prompt_template
from src.utils.json_utils import repair_json_output

from .types import State
from ..config import SELECTED_SEARCH_ENGINE, SearchEngine

logger = logging.getLogger(__name__)

@tool
def handoff_to_online_investigator(
    research_topic: Annotated[str, "research task"],
    locale: Annotated[str, "language locale (en-US, zh-CN)"],
):
    """
    This is a decorated function
    """
    return

@tool
def handoff_to_teach_planner(
    research_topic: Annotated[str, "research task"],
    locale: Annotated[str, "language locale (en-US, zh-CN)"],
):
    """
    This is a decorated function
    """
    return

@tool
def handoff_to_study_planner(
    research_topic: Annotated[str, "research task"],
    locale: Annotated[str, "language locale (en-US, zh-CN)"],
):
    """
    This is a decorated function
    """
    return

def teach_planner_node(state: State, config: RunnableConfig) -> Command[Literal["__end__"]]:
    logger.info("Teach plan node is running")
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    messages = apply_prompt_template("teach_planner", state, configurable)
    
    if configurable.enable_deep_thinking:
        llm = get_llm_by_type("reasoning")
    elif AGENT_LLM_MAP["teach_planner"] == "basic":
        llm = get_llm_by_type("basic").with_structured_output(
            Plan,
            method="json_mode",
        )
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["teach_planner"])
    
    # if plan_iterations >= configurable.max_plan_iterations:
    #     return Command(goto="reporter")
    
    full_response = ""
    if AGENT_LLM_MAP["teach_planner"] == "basic" and not configurable.enable_deep_thinking:
        response = llm.invoke(messages)
        full_response = response.model_dump_json(indent=4, exclude_none=True)
    else:
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content
    logger.debug(f"Current state messages: {state['messages']}")
    logger.info(f"Teach Planner response: {full_response}")
    
    try: 
        curr_plan = json.loads(repair_json_output(full_response))
    except json.JSONDecodeError:
        logger.warning("Teach Planner response is not a standard JSON")
    # 这里以后要加reporter
    if isinstance(curr_plan, dict) and curr_plan.get("has_enough_context"):
        logger.info("Teach Planner response has enough context")
        new_plan = Plan.model_validate(curr_plan)
        return Command(
            update = {
                "messages": [AIMessage(content=full_response, name="teach_planner")],
                "current_plan": new_plan,
            },
            #这里以后要加reporter
            goto= "__end__"
        )
    return Command(
        update={
            'messages': [AIMessage(content=full_response, name = "teach_planner")],
            "current_plan": full_response,
        },
        #这里以后要加human feedback
        goto="__end__"
    )
    
    
def study_planner_node(state: State, config: RunnableConfig) -> Command[Literal["__end__"]]:
    logger.info("Teach plan node is running")
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    messages = apply_prompt_template("study_planner", state, configurable)
    
    if configurable.enable_deep_thinking:
        llm = get_llm_by_type("reasoning")
    elif AGENT_LLM_MAP["study_planner"] == "basic":
        llm = get_llm_by_type("basic").with_structured_output(
            Plan,
            method="json_mode",
        )
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["study_planner"])
    
    # if plan_iterations >= configurable.max_plan_iterations:
    #     return Command(goto="reporter")
    
    full_response = ""
    if AGENT_LLM_MAP["study_planner"] == "basic" and not configurable.enable_deep_thinking:
        response = llm.invoke(messages)
        full_response = response.model_dump_json(indent=4, exclude_none=True)
    else:
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content
    logger.debug(f"Current state messages: {state['messages']}")
    logger.info(f"Study Planner response: {full_response}")
    
    try: 
        curr_plan = json.loads(repair_json_output(full_response))
    except json.JSONDecodeError:
        logger.warning("Study Planner response is not a standard JSON")
    # 这里以后要加reporter
    if isinstance(curr_plan, dict) and curr_plan.get("has_enough_context"):
        logger.info("Study Planner response has enough context")
        new_plan = Plan.model_validate(curr_plan)
        return Command(
            update = {
                "messages": [AIMessage(content=full_response, name="study_planner")],
                "current_plan": new_plan,
            },
            #这里以后要加reporter
            goto= "__end__"
        )
    return Command(
        update={
            'messages': [AIMessage(content=full_response, name = "study_planner")],
            "current_plan": full_response,
        },
        #这里以后要加human feedback
        goto="__end__"
    )
    

def coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["study_planner","teach_planner","online_investigator", "__end__"]]:
    logger.info("Coordinator is running")
    configurable = Configuration.from_runnable_config(config)
    messages = apply_prompt_template("coordinator", state)
    response = (
        get_llm_by_type(AGENT_LLM_MAP["coordinator"])
        .bind_tools([handoff_to_teach_planner,handoff_to_study_planner,handoff_to_online_investigator])
        .invoke(messages)
    )
    logger.debug(f"Current state messages: {state['messages']}")
    
    goto = "__end__"
    locale = state.get("locale", "zh-CN")
    research_topic = state.get("research_topic", "")
    
    if len(response.tool_calls) > 0:
        if state.get("enable_online_invest"):
            goto = "online_investigator"
    try:
        for tool_call in response.tool_calls:
            if tool_call.get("name") == "handoff_to_teach_planner":
                # Hand off to TP planner
                locale = tool_call.get("args", {}).get("locale", locale)
                research_topic = tool_call.get("args", {}).get("research_topic", research_topic)
                return Command(
                    update={
                        "locale": locale,
                        "research_topic": research_topic,
                        "resources": configurable.resources,
                    },
                    goto="teach_planner",  # Direct to TP planner
                )
            elif tool_call.get("name") == "handoff_to_study_planner":
                # Hand off to SP planner
                locale = tool_call.get("args", {}).get("locale", locale)
                research_topic = tool_call.get("args", {}).get("research_topic", research_topic)
                return Command(
                    update={
                        "locale": locale,
                        "research_topic": research_topic,
                        "resources": configurable.resources,
                    },
                    goto="study_planner",  # Direct to SP planner
                )
            elif tool_call.get("name") == "handoff_to_online_investigator":
                # Hand off to TP planner
                locale = tool_call.get("args", {}).get("locale", locale)
                research_topic = tool_call.get("args", {}).get("research_topic", research_topic)
                return Command(
                    update={
                        "locale": locale,
                        "research_topic": research_topic,
                        "resources": configurable.resources,
                    },
                    goto="online_investigator",  # Direct to TP planner
                )
            else:
                continue
    except Exception as e:
        logger.error(f"Error processing tool calls: {e}")
    else:
        logger.warning("Coordinator response contains no tool calls")
        logger.debug(f"Coordinator response: {response}")
    message = state.get("messages", [])
    if response.content:
        message.append(HumanMessage(content=response.content, name="coordinator"))
    return Command(
        update={
            "message": messages,
            "locale": locale,
            "research_topic": research_topic,
            "resources": configurable.resources,
        },
        goto = goto,
    )
    
def online_investigator_node(state: State, config: RunnableConfig):
    logger.info("online investigator node is running.")
    configurable = Configuration.from_runnable_config(config)
    query = state.get("research_topic")
    online_invest_results = None
    if SELECTED_SEARCH_ENGINE == SearchEngine.TAVILY.value:
        searched_content = LoggedTavilySearch(
            max_results=configurable.max_search_results
        ).invoke(query)
        if isinstance(searched_content, list):
            online_invest_results = [
                f"## {elem['title']}\n\n{elem['content']}" for elem in searched_content
            ]

            logger.info("according to online investigator's result, output again")
            messages = apply_prompt_template("online_investigator", state)
            messages.append(HumanMessage(content=f"online_invest_results: \n{online_invest_results}"))
            response = (
                get_llm_by_type(AGENT_LLM_MAP["online_investigator"])
                .bind_tools([])
                .invoke(messages)
            )
            logger.info(f"Online Investigator Response: {response.content}")
            logger.debug(f"Current state messages: {state['messages']}")
            return {
                "online_invest_results": "\n\n".join(
                    online_invest_results
                )
            }
        else:
            logger.error(
                f"Tavily search returned malformed response: {searched_content}"
            )
    else:
        online_invest_results = get_web_search_tool(
            configurable.max_search_results
        ).invoke(query)
      
    return {
        "online_invest_results": json.dumps(
            online_invest_results, ensure_ascii=False
        )
    }

