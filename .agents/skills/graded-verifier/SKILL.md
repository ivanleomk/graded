---
name: graded-verifier
description: Guidelines and code patterns for writing robust verifiers and evaluators using the graded framework, including criteria declaration, LLM judges, and trajectory checks.
---

# Graded Verifier Skill

This skill provides guidelines and patterns for writing defensive task verifiers using the `graded` framework.

## 1. Core Pattern

Always instantiate `Evaluator` with the workspace path, output JSON path, and optionally enable auto-saving of artifacts:

```python
from pathlib import Path
from graded import Evaluator

def main():
    ev = Evaluator(
        workspace="/app",  # or "/workspace" depending on task env
        output_path="/logs/verifier/reward.json"
    )
    
    # Define criteria here...
    
    ev.run()

if __name__ == "__main__":
    main()
```

## 2. Defining Criteria

Use the `@ev.criterion` decorator to declare checks.
- **Fatal checks**: Use `fatal=True` on gatekeeper checks (e.g. file existence) to immediately short-circuit the final reward to `0.0` on failure.
- **Fractional checks**: Return a float between `0.0` and `1.0` to award partial credit (e.g. test pass rate).
- **Weights**: Distribute weights to control the contribution of each check to the final average reward.

```python
@ev.criterion("file_exists", weight=0.1, fatal=True)
def check_file(workspace: Path) -> bool:
    return ev.file_exists("output.txt")

@ev.criterion("fractional_tests", weight=0.9)
def check_tests(workspace: Path) -> float:
    # return a float between 0.0 and 1.0
    return 0.8
```

## 3. LLM Judge with Structured Rubrics

For qualitative grading, use `ev.llm_judge` with a Pydantic model. 
* **Important**: Always query the judge lazily inside criteria functions to avoid execution errors if prerequisite files are missing.
* **Important**: The return value of `ev.llm_judge` is fully type-hinted to match the `response_model` class.

```python
from pydantic import BaseModel, Field

class QualityRubric(BaseModel):
    clarity: float = Field(description="Score 0.0-1.0 for writing clarity.")
    reasoning: str = Field(description="Reasoning explaining the score.")

# Cache the judge results to share one API call across multiple criteria
judge_cache = None

def get_judge(ev) -> QualityRubric:
    global judge_cache
    if judge_cache is None:
        content = ev.read_file("output.txt")
        if not content:
            return QualityRubric(clarity=0.0, reasoning="Empty file")
        judge_cache = ev.llm_judge(
            model="google/gemini-3.5-flash",
            response_model=QualityRubric,
            system="You are an expert editor.",
            prompt=f"Grade this content:\n\n{content}"
        )
    return judge_cache
```

## 4. Trajectory Checks

To check *how* the agent accomplished the task (e.g. checking tool usage, forbidden commands, or specific sequences):
1. Load the trajectory with `ev.load_trajectory()`.
2. Inspect the steps and tool calls using `trajectory.exists(function_name, predicate)`.
3. Use substring/inclusion checks (rather than exact string match) for arguments to handle chained commands.

```python
@ev.criterion("trajectory_check", weight=0.1)
def check_trajectory(workspace: Path) -> bool:
    trajectory = ev.load_trajectory()
    if not trajectory:
        return False
    
    # Check if agent called the 'bash' tool containing the command 'echo'
    return trajectory.exists(
        "bash",
        lambda tc: "echo" in tc.arg("command", "")
    )
```
