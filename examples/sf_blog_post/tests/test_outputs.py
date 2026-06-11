import sys
from pathlib import Path
from pydantic import BaseModel, Field
from graded import Evaluator

# Define the Pydantic schema for the LLM Judge
class BlogRubric(BaseModel):
    is_about_san_francisco: bool = Field(
        description="Whether the blog post is specifically about San Francisco."
    )
    professional_tone: bool = Field(
        description="Whether the blog post has a professional, engaging tone."
    )
    reasoning: str = Field(
        description="Detailed reasoning for the grading decision."
    )


def main():
    # Initialize the Evaluator for Harbor environment paths
    ev = Evaluator(
        workspace="/workspace",
        output_path="/logs/verifier/reward.json"
    )

    # 1. Gate: Verify the output file exists
    @ev.criterion("file_exists", weight=1.0, fatal=True)
    def check_file_exists(workspace: Path) -> bool:
        return ev.file_exists("blog-post.md")

    # 2. Check: Verify word count is at least 500 words
    @ev.criterion("word_count", weight=1.0)
    def check_word_count(workspace: Path) -> float:
        content = ev.read_file("blog-post.md")
        if not content:
            return 0.0
        words = content.split()
        word_count = len(words)
        
        # Give a fractional score if it's close, capped at 1.0
        return min(1.0, word_count / 500.0)

    # 3. Check: Verify content and tone using LLM Judge
    @ev.criterion("llm_judge_quality", weight=2.0)
    def check_content_quality(workspace: Path) -> float:
        content = ev.read_file("blog-post.md")
        if not content:
            return 0.0

        try:
            # Run the LLM Judge using instructor-based schema verification
            rubric = ev.llm_judge(
                response_model=BlogRubric,
                system="You are an expert editor grading a blog post submission.",
                prompt=f"Please grade the following blog post draft:\n\n{content}",
                model="google/gemini-3.5-flash",
            )
            
            # Print reasoning to stderr/logs for debugging
            print(f"Judge Reasoning: {rubric.reasoning}")

            # Both criteria must be satisfied for full credit
            if rubric.is_about_san_francisco and rubric.professional_tone:
                return 1.0
            
            # Partial credit if it meets at least one requirement
            if rubric.is_about_san_francisco or rubric.professional_tone:
                return 0.5
                
            return 0.0
        except Exception as e:
            # Fallback if API calls fail during evaluation
            print(f"LLM Judge execution failed: {e}")
            return 0.0

    # Run the evaluation pipeline
    ev.run()


if __name__ == "__main__":
    main()
