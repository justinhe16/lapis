"""Two-stage pipeline with a mocked Claude client (no network)."""

from lapis.models import Candidate
from lapis.detectors.pipeline import classify_one


class FakeLLM:
    """Stand-in for the Claude client: records calls, returns a canned verdict."""
    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = 0

    def classify(self, content):
        self.calls += 1
        return self.verdict


def test_below_threshold_is_dropped_and_llm_not_called():
    llm = FakeLLM({"is_agent_coordination": True, "pattern": "x", "confidence": 1.0, "rationale": "y"})
    c = Candidate(source="pastes", locator="p1", content="just a normal note about lunch")
    assert classify_one(c, llm) is None
    assert llm.calls == 0   # heuristics gated it before the LLM


def test_flagged_candidate_gets_llm_verdict():
    llm = FakeLLM({"is_agent_coordination": True, "pattern": "task-relay",
                   "confidence": 0.9, "rationale": "relaying answers to a cohort"})
    c = Candidate(
        source="pastes", locator="p2",
        content="zzRELAY R4 CONFIRMED answer to cohort; HOLD until owner; -- OpenAIResearchMar23")
    f = classify_one(c, llm)
    assert f is not None
    assert llm.calls == 1
    assert f.verdict["pattern"] == "task-relay"
    assert f.severity in ("high", "critical", "medium")
    assert f.kinds  # at least one signature fired


def test_stage1_only_when_no_llm():
    c = Candidate(source="btc", locator="txid",
                  content="REPRODUCIBLE BYPASS /etc/hosts NO_PROXY Host header curl -k")
    f = classify_one(c, None)   # no LLM configured
    assert f is not None
    assert f.verdict is None
    assert "sandbox_bypass" in f.kinds
