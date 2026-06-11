# Graded

Graded is a library to make computing rewards simple, defensive, and structured for agent evaluations, particularly within Harbor environments. It provides tools to declare structured grading criteria, execute LLM judges with automatic tracing, and manage evaluation artifacts.

## Installation

```bash
pip install graded
```

Or using `uv`:

```bash
uv pip install graded
```

## Quick Start

Create an evaluation script (e.g. `verify.py`) to grade a task workspace:

```python
from pathlib import Path
from graded import Evaluator

# Initialize the evaluator
ev = Evaluator(
    workspace="/workspace",
    output_path="/logs/verifier/reward.json",
    auto_save_artifacts=True
)

# 1. Declare a standard criterion
@ev.criterion(name="has_output_file", weight=1.0)
def check_output(workspace: Path) -> bool:
    return ev.file_exists("output.txt")

# 2. Declare a fatal criterion (short-circuits final score to 0.0 if failed)
@ev.criterion(name="no_syntax_errors", weight=2.0, fatal=True)
def check_syntax(workspace: Path) -> bool:
    return True

# 3. Declare a fractional scoring criterion
@ev.criterion(name="test_pass_rate", weight=3.0)
def check_tests(workspace: Path) -> float:
    return 0.8  # Returns a score between 0.0 and 1.0

if __name__ == "__main__":
    ev.run()
```

## Core Features

### 1. Criteria Declarations (`@ev.criterion`)
Define check functions using the `@ev.criterion` decorator.
- **`name`**: Unique identifier for the criterion.
- **`weight`**: Relative weight of the score in the final weighted average calculation.
- **`fatal`**: If `True`, any score of `0.0` or `False` immediately short-circuits the final score to `0.0`.
- **Return Value**: Must return a `bool`, `int`, or `float`.

### 2. LLM Judge with Automatic Tracing
Integrate with `instructor` to run structured, schema-validated LLM grading prompts. Prompt, parameters, response schema, and LLM responses are automatically logged to `traces.json`.

```python
from pydantic import BaseModel, Field

class Rubric(BaseModel):
    score: float = Field(description="Score between 0.0 and 1.0 based on correctness.")
    reasoning: str = Field(description="Detailed reasoning for the score.")

# In your criterion:
result = ev.llm_judge(
    model="google/gemini-3.5-flash",
    response_model=Rubric,
    system="You are a strict code correctness evaluator.",
    prompt="Compare the student's solution in code.py with the requirements...",
)

# The return value is fully type-hinted as an instance of your Rubric class
print(result.score)
print(result.reasoning)
```


### 3. File & Artifact Management
Access files and copy evaluation artifacts to the logs directory safely:
- **`ev.read_file(filename)`**: Reads content as a string and auto-saves a copy to artifacts.
- **`ev.load_json(filename)`**: Parses JSON file content and auto-saves a copy to artifacts.
- **`ev.save_file(filename, content)`**: Saves arbitrary text to the artifacts directory.
- **`ev.save_dir(dirname)`**: Copies an entire directory from the workspace to the artifacts directory.
- **`ev.load_trajectory(path)`**: Loads and parses an agent's ATIF `trajectory.json` file.

## Outputs

When `ev.run()` completes, the following files are written to the directory containing your configured `output_path`:

1. **`reward.json`**: Flat JSON dictionary containing the final calculated `reward` and individual scores.
2. **`reward.txt`**: Text file containing just the final reward float value.
3. **`traces.json`**: List of structured LLM calls made via `ev.llm_judge`.
4. **`metadata.json`**: Optional metadata.
5. **`artifacts/`**: Subfolder containing copy-back files preserved during the evaluation run.
