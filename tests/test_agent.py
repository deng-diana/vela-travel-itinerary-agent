from src.agent.orchestrator import AgentOrchestrator


def test_orchestrator_weather():
    orch = AgentOrchestrator()
    reply, used = orch.run("上海天气怎么样？")
    assert isinstance(reply, str) and reply
    assert used and used[0].name == "get_weather"


def test_orchestrator_fallback():
    orch = AgentOrchestrator()
    reply, used = orch.run("你好")
    assert isinstance(reply, str) and reply
    assert used == []

