# Graded Examples 🚀

This directory contains example tasks showing how to use `graded` inside a Harbor evaluation workflow.

---

## 1. San Francisco Blog Post (`sf_blog_post`)
This is a standard Harbor-compatible task configuration that asks an agent to draft a 500-word blog post about San Francisco.

### Files
* **`task.toml`**: Configures the task identity and execution constraints.
* **`instruction.md`**: The explicit prompt presented to the agent.
* **`environment/Dockerfile`**: A lightweight Python environment where the task is executed.
* **`solution/solve.sh`**: The oracle solution script that automatically produces a passing `blog-post.md` file.
* **`tests/test.sh`**: The test entrypoint script called by Harbor.
* **`tests/test_outputs.py`**: The verification script using `graded.Evaluator` with four criteria:
  1. `file_exists` (weight = `0.1`, fatal check)
  2. `clarity` (weight = `0.4`, evaluated via LLM judge)
  3. `succinctness` (weight = `0.4`, evaluated via LLM judge)
  4. `trajectory_check` (weight = `0.1`, verifies that `echo "hello world!"` was executed)

---

## Running with Harbor

To run this evaluation task locally using the Harbor CLI and the `oracle` agent:

```bash
harbor run -p examples -a oracle -i graded/sf-blog-post
```

Harbor will:
1. Build the Docker environment.
2. Spin up the container.
3. Run `solve.sh` (under the `oracle` agent).
4. Run `test_outputs.py` to evaluate the workspace outputs and write rewards.

---

## Sample Job Outputs
We have included a sample run of this job under [sf_blog_post/sample_job/](sf_blog_post/sample_job/) for reference:
* **`result.json`**: Trial metadata, runtime breakdowns, and final verifier results.
* **`trial.log`**: Standard output logs from the container environment setup.
* **`verifier/reward.json`**: Flat dictionary containing the computed reward and individual criteria scores:
  ```json
  {
    "reward": 1.0,
    "file_exists": 1.0,
    "clarity": 1.0,
    "succinctness": 1.0,
    "trajectory_check": 1.0
  }
  ```
* **`verifier/test-stdout.txt`**: Standard output from the verifier script execution.
