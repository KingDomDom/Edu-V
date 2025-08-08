import logging
from src.config.configuration import get_recursion_limit
from src.graph import build_graph

logging.basicConfig(
    level= logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

def enable_debug_logging():
    logging.getLogger("src").setLevel(logging.DEBUG)
    
logger = logging.getLogger(__name__)

graph = build_graph()

async def run_agent_workflow_async(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_online_invest: bool = True,
):
    if not user_input:
        raise ValueError("empty input")
    
    if debug:
        enable_debug_logging()
        
    logger.info(f"Starting async workflow from user input: {user_input}")
    initial_state = {
        "messages": [{"role": "user", "content": user_input}],
        "auto_accepted_plan": True,
        "enable_online_invest": enable_online_invest,
    }
    config = {
        "configurable":{
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "mcp_settings":{
                "servers":{
                    "mcp-github-trending":{
                        "transport": "stdio",
                        "command": "cmd",
                        "args":[
                            "mcp-github-trending"
                        ],
                        "enabled_tools": ["get_github_trending_repositories"],
                        "add_to_agents": ["coordinator"],
                    }
                }
            },
        },
        "recursion_limit": get_recursion_limit(default = 100)
    }
    last_message_cnt = 0
    async for s in graph.astream(
        input = initial_state, config=config, stream_mode="values"
    ):
        try:
            if isinstance(s, dict) and "messages" in s:
                if len(s["messages"]) <= last_message_cnt:
                    continue
                last_message_cnt = len(s["messages"])
                message = s["messages"][-1]
                if isinstance(message, tuple):
                    print(message)
                else:
                    message.pretty_print()
            else:
                print(f"Output: {s}")
        except Exception as e:
            logger.error(f"Error processing stream output: {e}")
            print(f"Error processing output: {str(e)}")
    logger.info("Async workflow completed successfully")
    
if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid)