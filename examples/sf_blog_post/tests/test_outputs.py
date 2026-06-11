from pathlib import Path
from pydantic import BaseModel, Field
from graded import Evaluator


class StyleRubric(BaseModel):
    clarity: float = Field(
        description="Score between 0.0 and 1.0. Is the writing clear, concise, and easy to understand?"
    )
    succinctness: float = Field(
        description="Score between 0.0 and 1.0. Is the writing succinct, avoiding unnecessary fluff, redundancy, or repetitive phrasing?"
    )
    reasoning: str = Field(
        description="Detailed explanation justifying the scores for clarity and succinctness."
    )


def main():
    ev = Evaluator(workspace="/app", output_path="/logs/verifier/reward.json")

    # 1. Verify the file exists and is readable
    @ev.criterion("file_exists", weight=0.1, fatal=True)
    def check_file_exists(workspace: Path) -> bool:
        return ev.file_exists("blog-post.md")

    # Cache the LLM judge result to share it across multiple criteria
    judge_result = None

    def get_judge_result() -> StyleRubric:
        nonlocal judge_result
        if judge_result is None:
            content = ev.read_file("blog-post.md")
            if not content:
                return StyleRubric(clarity=0.0, succinctness=0.0, reasoning="Empty or missing file")

            judge_result = ev.llm_judge(
                model="google/gemini-3.5-flash",
                response_model=StyleRubric,
                system="You are an expert editor grading blog posts.",
                prompt=f"Please grade the clarity and succinctness of this blog post:\n\n{content}",
            )
        return judge_result

    # 2. Clarity Quality Check
    @ev.criterion("clarity", weight=0.4)
    def check_clarity(workspace: Path) -> float:
        res = get_judge_result()
        return res.clarity

    # 3. Succinctness Quality Check
    @ev.criterion("succinctness", weight=0.4)
    def check_succinctness(workspace: Path) -> float:
        res = get_judge_result()
        return res.succinctness

    # 4. Trajectory Check: Verify echo "hello world!" was called
    @ev.criterion("trajectory_check", weight=0.1)
    def check_trajectory(workspace: Path) -> bool:
        trajectory = ev.load_trajectory()
        if not trajectory:
            return False

        def is_hello_world_command(tc) -> bool:
            cmd = tc.arg("command", "").strip()
            return 'echo "hello world!"' in cmd.replace("'", '"')

        return trajectory.exists("bash", is_hello_world_command)


    ev.run()


if __name__ == "__main__":
    main()

