"""Agent 管理 API 路由"""
from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

# 模拟的 Agent 状态数据
# 实际实现中应该从 Helen 运行时获取
agent_states = {
    "Contractor": {"status": "idle", "last_task": None},
    "TestBuilder": {"status": "idle", "last_task": None},
    "Implementer": {"status": "idle", "last_task": None},
    "QualityGate": {"status": "idle", "last_task": None},
    "SkillEvaluator": {"status": "idle", "last_task": None},
}

@router.get("/status")
async def get_all_agents_status():
    """获取所有 Agent 状态"""
    return agent_states

@router.get("/{agent_name}/status")
async def get_agent_status(agent_name: str):
    """获取单个 Agent 状态"""
    if agent_name not in agent_states:
        return {"error": f"Agent {agent_name} not found"}
    return {
        "name": agent_name,
        **agent_states[agent_name]
    }

@router.get("/list")
async def list_agents():
    """列出所有可用的 Agent"""
    return list(agent_states.keys())
