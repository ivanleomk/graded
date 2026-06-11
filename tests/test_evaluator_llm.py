import os
import pytest
from pydantic import BaseModel, Field
from conftest import DummyRubric


def test_llm_judge_real_success(workspace_setup):
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY environment variable not set")

    ev = workspace_setup["evaluator"]

    result = ev.llm_judge(
        model="google/gemini-3.5-flash",
        response_model=DummyRubric,
        system="You are a strict helper grader.",
        prompt="Please grade the politeness of this string: 'Hello, could you please help me with my task?'",
    )

    assert isinstance(result, DummyRubric)
    assert 0.0 <= result.score <= 1.0
    assert len(result.reasoning) > 0

    # Verify traces are stored
    assert len(ev.traces) == 1
    assert ev.traces[0] == {
        "model": "google/gemini-3.5-flash",
        "system": "You are a strict helper grader.",
        "prompt": "Please grade the politeness of this string: 'Hello, could you please help me with my task?'",
        "kwargs": {},
        "response_model_schema": DummyRubric.model_json_schema(),
        "status": "success",
        "response": {"score": result.score, "reasoning": result.reasoning},
        "metadata": {},
    }


def test_llm_judge_real_failure(workspace_setup):
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY environment variable not set")

    ev = workspace_setup["evaluator"]

    # Use an invalid model name to force a real API / SDK validation error
    with pytest.raises(Exception) as exc_info:
        ev.llm_judge(
            model="google/invalid-model-name-does-not-exist",
            response_model=DummyRubric,
            system="be strict",
            prompt="evaluate guide",
        )

    # Verify traces recorded failure
    assert len(ev.traces) == 1
    assert ev.traces[0] == {
        "model": "google/invalid-model-name-does-not-exist",
        "system": "be strict",
        "prompt": "evaluate guide",
        "kwargs": {},
        "response_model_schema": DummyRubric.model_json_schema(),
        "status": "failed",
        "error": str(exc_info.value),
        "metadata": {},
    }
