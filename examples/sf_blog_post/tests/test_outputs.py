from pathlib import Path
from graded import Evaluator


def main():
    ev = Evaluator(
        workspace="/app",
        output_path="/logs/verifier/reward.json"
    )

    # 1. Verify the file exists and is readable
    @ev.criterion("file_exists", weight=0.5, fatal=True)
    def check_file_exists(workspace: Path) -> bool:
        content = ev.read_file("blog-post.md")
        return content is not None

    # 2. Verify word count is at least 500 words
    @ev.criterion("word_count", weight=0.5)
    def check_word_count(workspace: Path) -> bool:
        content = ev.read_file("blog-post.md")
        if not content:
            return False
        return len(content.split()) >= 500

    ev.run()


if __name__ == "__main__":
    main()
