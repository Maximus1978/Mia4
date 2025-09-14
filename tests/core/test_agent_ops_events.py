from core.llm.agent_ops import judge, plan
from core.events import on, reset_listeners_for_tests


def test_judge_event_emitted():
    events = []
    on(lambda n, p: events.append((n, p)))
    res = judge(target_request_id="req123", prompt="Test answer quality")
    assert res["agreement"] is not None
    names = [n for n, _ in events]
    assert "JudgeInvocation" in names
    assert "ReasoningPresetApplied" in names
    reset_listeners_for_tests()


def test_plan_event_emitted():
    events = []
    on(lambda n, p: events.append((n, p)))
    res = plan(objective="Implement idle sweep", max_steps=5)
    assert len(res["steps"]) >= 1
    names = [n for n, _ in events]
    assert "PlanGenerated" in names
    assert "ReasoningPresetApplied" in names
    reset_listeners_for_tests()
