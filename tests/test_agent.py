from src.agent.orchestrator import AgentOrchestrator
from src.agent.state import ConversationState


class _FakeResponse:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class _FakeMessages:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return _FakeResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "get_weather",
                        "input": {"destination": "Tokyo", "month": "August"},
                    }
                ],
                stop_reason="tool_use",
            )
        return _FakeResponse(
            content=[{"type": "text", "text": "Tokyo looks warm and humid in August."}],
            stop_reason="end_turn",
        )


class _FakeClient:
    def __init__(self):
        self.messages = _FakeMessages()


def test_orchestrator_handles_tool_loop():
    orchestrator = AgentOrchestrator(client=_FakeClient(), model="fake-model")
    state = ConversationState(session_id="session-1")

    result = orchestrator.run(state=state, user_message="Plan Tokyo in August")

    assert "Tokyo" in result.reply
    assert any(event.tool_name == "get_weather" for event in result.events if event.tool_name)


def test_orchestrator_keeps_state_messages():
    orchestrator = AgentOrchestrator(client=_FakeClient(), model="fake-model")
    state = ConversationState(session_id="session-2")

    orchestrator.run(state=state, user_message="Plan Tokyo in August")

    assert state.messages
