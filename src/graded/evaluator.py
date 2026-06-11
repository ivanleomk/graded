import os
import json
import shutil
import logging
from pathlib import Path
from typing import Callable, Any, Dict, List, Optional, Type, Union, TypeVar
from pydantic import BaseModel

from graded.types import Criterion, Trajectory

T = TypeVar("T", bound=BaseModel)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


class Evaluator:
    def __init__(
        self,
        workspace: Union[str, Path] = "/workspace",
        output_path: Union[str, Path] = "/logs/verifier/reward.json",
        auto_save_artifacts: bool = True,
        artifacts_dir: Optional[Union[str, Path]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.workspace = Path(workspace)
        self.output_path = Path(output_path)
        self.auto_save_artifacts = auto_save_artifacts
        self.artifacts_dir = (
            Path(artifacts_dir)
            if artifacts_dir
            else self.output_path.parent / "artifacts"
        )
        self.metadata: Dict[str, Any] = metadata or {}
        self.criteria: List[Criterion] = []
        self.scores: Dict[str, float] = {}
        self.traces: List[Dict[str, Any]] = []

    def criterion(self, name: str, weight: float = 1.0, fatal: bool = False):
        """Decorator to declare a grading criterion.

        Args:
            name: Name of the criterion.
            weight: Relative weight for scoring.
            fatal: If True, a score of 0.0 short-circuits the entire evaluation to 0.0.
        """

        def decorator(func: Callable[[Path], Any]):
            if any(c.name == name for c in self.criteria):
                raise ValueError(f"Duplicate criterion name: '{name}'")
            self.criteria.append(
                Criterion(name=name, weight=weight, fatal=fatal, func=func)
            )
            return func

        return decorator

    def _save_artifact(self, filename: str, content: str) -> None:
        """Internal helper to save content to the artifacts directory."""
        try:
            dest = self.artifacts_dir / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        except Exception as e:
            logging.error(f"Failed to save artifact {filename}: {e}")

    def save_file(self, filename: str, content: str) -> None:
        """Explicitly save content to the artifacts directory."""
        self._save_artifact(filename, content)

    def save_dir(self, dirname: str) -> None:
        """Copy an entire directory from the workspace to the artifacts directory."""
        src = self.workspace / dirname
        dest = self.artifacts_dir / dirname
        if not src.is_dir():
            logging.warning(f"Directory {dirname} not found in workspace.")
            return
        try:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
        except Exception as e:
            logging.error(f"Failed to save directory artifact {dirname}: {e}")

    def load_json(
        self, filename: str, save_artifact: Optional[bool] = None
    ) -> Optional[Any]:
        """Safely loads and parses JSON from the workspace.

        Args:
            filename: Path relative to the workspace.
            save_artifact: Whether to save a copy to the artifacts directory.
                Defaults to the instance-level auto_save_artifacts setting.
        """
        path = self.workspace / filename
        if not path.exists():
            logging.warning(f"File {filename} not found in workspace.")
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            should_save = (
                save_artifact if save_artifact is not None else self.auto_save_artifacts
            )
            if should_save:
                self._save_artifact(filename, raw)
            return json.loads(raw)
        except Exception as e:
            logging.error(f"Error parsing JSON file {filename}: {e}")
            return None

    def read_file(
        self, filename: str, save_artifact: Optional[bool] = None
    ) -> Optional[str]:
        """Safely reads file content from the workspace.

        Args:
            filename: Path relative to the workspace.
            save_artifact: Whether to save a copy to the artifacts directory.
                Defaults to the instance-level auto_save_artifacts setting.
        """
        path = self.workspace / filename
        if not path.exists():
            logging.warning(f"File {filename} not found in workspace.")
            return None
        try:
            content = path.read_text(encoding="utf-8")
            should_save = (
                save_artifact if save_artifact is not None else self.auto_save_artifacts
            )
            if should_save:
                self._save_artifact(filename, content)
            return content
        except Exception as e:
            logging.error(f"Error reading file {filename}: {e}")
            return None

    def load_trajectory(
        self, path: str = "/logs/agent/trajectory.json"
    ) -> Optional[Trajectory]:
        """Load and parse the ATIF trajectory written by the agent.

        Args:
            path: Absolute path to the trajectory JSON file.
                  Defaults to ``/logs/agent/trajectory.json``.

        Returns:
            A typed :class:`Trajectory` on success, or ``None`` if the file is
            missing or unparseable (a warning is logged in either case).
        """
        traj_path = Path(path)
        if not traj_path.exists():
            logging.warning(f"Trajectory file not found: {path}")
            return None
        try:
            return Trajectory.model_validate_json(traj_path.read_text(encoding="utf-8"))
        except Exception as e:
            logging.error(f"Failed to parse trajectory at {path}: {e}")
            return None

    def file_exists(self, filename: str) -> bool:
        """Checks if a file exists in the workspace."""
        path = self.workspace / filename
        return path.is_file()

    def dir_exists(self, dirname: str) -> bool:
        """Checks if a directory exists in the workspace."""
        path = self.workspace / dirname
        return path.is_dir()

    def llm_judge(
        self,
        response_model: Type[T],
        system: str,
        prompt: str,
        model: str,
        client: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> T:
        """Call instructor LLM judge with structured responses and trace the call.

        Args:
            response_model: Pydantic model for structured output.
            system: System prompt text.
            prompt: User prompt text.
            model: Model identifier (e.g. "google/gemini-3.1-flash-lite").
            client: Optional pre-configured instructor client.
            metadata: Optional per-call metadata dict. Merged with evaluator-level
                metadata for experiment tracking.
            **kwargs: Additional arguments passed to client.create().
        """
        import instructor

        call_metadata = metadata or {}

        # Merge metadata: evaluator-level -> per-call
        merged_metadata = {
            **self.metadata,
            **call_metadata,
        }

        trace_data = {
            "model": model,
            "system": system,
            "prompt": prompt,
            "kwargs": {k: repr(v) for k, v in kwargs.items()},
            "response_model_schema": response_model.model_json_schema(),
            "metadata": merged_metadata,
        }

        try:
            if client is None:
                client = instructor.from_provider(model=model)

            model_name = model.split("/")[-1]
            result = client.create(
                model=model_name,
                response_model=response_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                **kwargs,
            )
            # Record trace on success
            success_trace = {
                **trace_data,
                "response": result.model_dump(),
                "status": "success",
            }
            self.traces.append(success_trace)
            return result
        except Exception as e:
            # Record trace on failure
            failed_trace = {
                **trace_data,
                "error": str(e),
                "status": "failed",
            }
            self.traces.append(failed_trace)
            raise e

    def _score_criterion(self, crit: Criterion) -> float:
        """Run a single criterion and coerce its result to a float score.

        A crash inside the criterion is caught and scored 0.0. A return value
        that is not ``bool | int | float`` raises ``ValueError`` (a likely
        forgotten ``return``).
        """
        try:
            res = crit.func(self.workspace)
        except Exception as e:
            logging.error(
                f"Failed executing criterion '{crit.name}': {e}", exc_info=True
            )
            print(
                f"CRITERION: {crit.name} (weight={crit.weight}) -> FAILED (Score: 0.0)"
            )
            return 0.0

        if not isinstance(res, (bool, int, float)):
            raise ValueError(
                f"Criterion '{crit.name}' must return bool | int | float, "
                f"got {type(res).__name__}. Did you forget a return?"
            )

        score = float(res)  # float(True) == 1.0, float(False) == 0.0
        print(f"CRITERION: {crit.name} (weight={crit.weight}) -> Score: {score}")
        return score

    def run(self):
        """Executes all criteria, aggregates weighted scores, and writes outputs."""
        total_weight = 0.0
        weighted_score = 0.0

        print("=== Start Evaluation ===")
        for crit in self.criteria:
            total_weight += crit.weight
            score = self._score_criterion(crit)
            self.scores[crit.name] = score
            weighted_score += score * crit.weight

            if crit.fatal and score == 0.0:
                print(
                    f"FATAL: Criterion '{crit.name}' failed. Short-circuiting to 0.0."
                )
                self._write_outputs(0.0)
                return

        final_reward = (weighted_score / total_weight) if total_weight > 0 else 0.0
        self._write_outputs(final_reward)

    def _write_outputs(self, final_reward: float):
        """Write all output files (reward, traces)."""
        print(f"Final Computed Reward: {final_reward:.4f}")

        # Ensure output directories exist
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write legacy reward.txt format
        reward_txt = self.output_path.with_name("reward.txt")
        try:
            reward_txt.write_text(f"{final_reward:.4f}\n")
        except Exception as e:
            logging.error(f"Failed to write reward.txt: {e}")

        # Write structured reward.json — flat dict[str, float|int] for Harbor compatibility
        # Each criterion score is a top-level key alongside 'reward'
        output_data = {"reward": final_reward, **self.scores}
        try:
            self.output_path.write_text(json.dumps(output_data, indent=2))
        except Exception as e:
            logging.error(f"Failed to write reward.json: {e}")

        # Write metadata.json if metadata was provided
        if self.metadata:
            metadata_path = self.output_path.parent / "metadata.json"
            try:
                metadata_path.write_text(json.dumps(self.metadata, indent=2))
            except Exception as e:
                logging.error(f"Failed to write metadata.json: {e}")

        # Write LLM judge traces
        traces_path = self.output_path.parent / "traces.json"
        try:
            traces_path.write_text(json.dumps(self.traces, indent=2))
        except Exception as e:
            logging.error(f"Failed to write traces.json: {e}")

        print("=== Evaluation Finished ===")
