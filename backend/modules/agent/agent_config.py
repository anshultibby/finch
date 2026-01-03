"""
Agent Configuration - Two-tier agent system

Based on Anthropic's "Effective harnesses for long-running agents":
- Master Agent: Planning, coordination, writes _tasks.md, reviews results
- Executor Agent: Reads _tasks.md, executes tasks, marks them done

All agent configuration (model, tools, prompts) is centralized here.
"""
from config import Config
from .prompts import get_master_agent_prompt, get_executor_agent_prompt


def create_master_agent(context):
    """
    Create the Master Agent.
    
    Master Agent:
    - Plans and coordinates
    - Writes _tasks.md with checklist
    - Delegates to Executor via delegate_execution()
    - Reviews results and updates tasks
    """
    from .base_agent import BaseAgent
    
    return BaseAgent(
        context=context,
        system_prompt=get_master_agent_prompt(),
        model=Config.MASTER_LLM_MODEL,
        tool_names=Config.MASTER_AGENT_TOOLS,
        enable_tool_streaming=True
    )


def create_executor_agent(context):
    """
    Create the Executor Agent.
    
    Executor Agent:
    - Reads _tasks.md
    - Works through unchecked tasks
    - Marks tasks complete
    - Calls finish_execution when done
    """
    from .base_agent import BaseAgent
    
    return BaseAgent(
        context=context,
        system_prompt=get_executor_agent_prompt(),
        model=Config.EXECUTOR_LLM_MODEL,
        tool_names=Config.EXECUTOR_AGENT_TOOLS,
        enable_tool_streaming=True
    )


def create_main_agent(context):
    """
    Create single agent with base tools (legacy/simple mode).
    """
    from .base_agent import BaseAgent
    
    return BaseAgent(
        context=context,
        system_prompt=get_master_agent_prompt(),
        model=Config.MASTER_LLM_MODEL,
        tool_names=Config.AGENT_TOOLS,
        enable_tool_streaming=True
    )
