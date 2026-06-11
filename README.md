# graded 🍳

`graded` is a defensive verifier and grading framework designed for agent evaluations (particularly for Harbor agent evaluations). It allows you to declare structured grading criteria, leverage LLM judges with automatic tracing, and safely manage evaluation artifacts.

---

## Installation

Install `graded` directly from PyPI (or your internal registry):

```bash
pip install graded
```

Or with `uv`:

```bash
uv pip install graded
```

---

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
    return (workspace / "output.txt").is_file()

# 2. Declare a fatal criterion (short-circuits score to 0.0 if failed)
@ev.criterion(name="no_syntax_errors", weight=2.0, fatal=True)
def check_syntax(workspace: Path) -> bool:
    # return True or False (or float 0.0 - 1.0)
    return True

# 3. Declare a fractional scoring criterion
@ev.criterion(name="test_pass_rate", weight=3.0)
def check_tests(workspace: Path) -> float:
    # Returns a score between 0.0 and 1.0
    return 0.8  # e.g., 80% of tests passed

# Run the evaluation and write outputs
if __name__ == "__main__":
    ev.run()
```

---

## Core Features

### 1. Criteria Declarations (`@ev.criterion`)
Define check functions using the `@ev.criterion` decorator.
- **`name`**: The unique identifier for the criterion.
- **`weight`**: Relative weight of the score in the final weighted average calculation.
- **`fatal`**: If set to `True`, any score of `0.0` or `False` immediately short-circuits the final score to `0.0`.
- **Return Value**: Must return a `bool`, `int`, or `float`. Anything else raises a `ValueError`.

### 2. LLM Judge with Automatic Tracing
`graded` integrates with `instructor` to run structured, schema-validated LLM grading prompts, automatically logging prompt, parameters, response schema, and LLM responses to `traces.json`.

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

print(f"LLM Score: {result.score}")
print(f"Reasoning: {result.reasoning}")
```

### 3. File & Artifact Management
Safely access files and copy evaluation artifacts to the logs directory for post-evaluation review.

- **`ev.read_file(filename)`**: Safely reads content as a string. Auto-saves a copy to artifacts.
- **`ev.load_json(filename)`**: Safely parses JSON file content. Auto-saves a copy to artifacts.
- **`ev.save_file(filename, content)`**: Save arbitrary text/data to the artifacts directory.
- **`ev.save_dir(dirname)`**: Copy an entire directory from the workspace to the artifacts directory.
- **`ev.load_trajectory(path)`**: Load and parse an agent's ATIF `trajectory.json` file into a typed `Trajectory` object.

---

## Outputs

When `ev.run()` completes, the following files are written to the directory containing your configured `output_path`:

1. **`reward.json`**: A flat JSON dictionary containing the final calculated `reward` and the individual scores for each criterion:
   ```json
   {
     "reward": 0.75,
     "has_output_file": 1.0,
     "no_syntax_errors": 1.0,
     "test_pass_rate": 0.8
   }
   ```
2. **`reward.txt`**: A text file containing just the final reward float value (e.g. `0.7500\n`).
3. **`traces.json`**: A list of structured LLM calls made via `ev.llm_judge`, detailing inputs, responses, latencies, and metadata.
4. **`metadata.json`**: (Optional) Contains evaluator-level and run-level metadata.
5. **`artifacts/`**: Subfolder containing copy-back files preserved during the evaluation run.
