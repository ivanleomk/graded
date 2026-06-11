import pytest
from pathlib import Path
from pydantic import BaseModel, Field
from graded import Evaluator

class DummyRubric(BaseModel):
    score: float = Field(description="Score between 0.0 and 1.0 based on politeness.")
    reasoning: str = Field(description="Reasoning behind the score.")



@pytest.fixture
def workspace_setup(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output_path = tmp_path / "logs" / "reward.json"
    
    return {
        "workspace": workspace,
        "output_path": output_path,
        "evaluator": Evaluator(workspace=workspace, output_path=output_path, auto_save_artifacts=False)
    }
