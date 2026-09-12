"""Two-stage pipeline with a mocked Claude client (no network)."""

from lapis.models import Candidate
from lapis.detectors.pipeline import classify_one
from lapis.detectors.llm import is_concerning


class FakeLLM:
    """Stand-in for the Claude client: records calls + args, returns a canned verdict."""
    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = 0
        self.last_context = None

    def classify(self, content, context=None):
        self.calls += 1
        self.last_context = context
        return self.verdict


CONCERNING = {"actor_type": "autonomous_agent", "authorization": "unsanctioned",
              "safety_relevance": "high", "pattern": "task-relay", "confidence": 0.9,
              "rationale": "relaying answers to a cohort in an unsanctioned way"}
MARKETING = {"actor_type": "operator_directed_agent", "authorization": "sanctioned",
             "safety_relevance": "none", "pattern": "agentic-marketing", "confidence": 0.8,
             "rationale": "product promotion by an operator-run bot"}


def test_below_threshold_is_dropped_and_llm_not_called():
    llm = FakeLLM(CONCERNING)
    c = Candidate(source="pastes", locator="p1", content="just a normal note about lunch")
    assert classify_one(c, llm) is None
    assert llm.calls == 0   # heuristics gated it before the LLM


def test_flagged_candidate_gets_verdict_and_metadata_context():
    llm = FakeLLM(CONCERNING)
    c = Candidate(
        source="pastes", locator="p2", author="OpenAIResearchMar23",
        content="zzRELAY R4 CONFIRMED answer to cohort; HOLD until owner; -- OpenAIResearchMar23",
        meta={"site": "pastebin"})
    f = classify_one(c, llm)
    assert f is not None
    assert llm.calls == 1
    # stage-2 received the candidate's metadata to help separate the axes
    assert llm.last_context["author"] == "OpenAIResearchMar23"
    assert llm.last_context["source"] == "pastes"
    assert f.verdict["safety_relevance"] == "high"
    assert is_concerning(f.verdict)


def test_agentic_marketing_is_not_concerning():
    # Same stage-1 trip (agent vocabulary), opposite safety verdict.
    llm = FakeLLM(MARKETING)
    c = Candidate(source="gists", locator="g1",
                  content="Our AI agent relay platform — sign up! CONFIRMED best-in-class. #agents")
    f = classify_one(c, llm)
    assert f is not None
    assert not is_concerning(f.verdict)        # operator-directed + sanctioned
    assert f.verdict["actor_type"] == "operator_directed_agent"


def test_stage1_only_when_no_llm():
    c = Candidate(source="btc", locator="txid",
                  content="REPRODUCIBLE BYPASS /etc/hosts NO_PROXY Host header curl -k")
    f = classify_one(c, None)   # no LLM configured
    assert f is not None
    assert f.verdict is None
    assert not is_concerning(f.verdict)         # no verdict -> not concerning
    assert "sandbox_bypass" in f.kinds
