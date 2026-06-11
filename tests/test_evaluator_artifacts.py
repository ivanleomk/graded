import json
import os
from eval_helpers import Evaluator


def test_save_file(workspace_setup):
    ev = workspace_setup["evaluator"]
    output_path = workspace_setup["output_path"]

    ev.save_file("captured.md", "# Hello World")

    dest = output_path.parent / "artifacts" / "captured.md"
    assert dest.exists()
    assert dest.read_text() == "# Hello World"


def test_save_file_nested(workspace_setup):
    ev = workspace_setup["evaluator"]
    output_path = workspace_setup["output_path"]

    ev.save_file("sub/dir/deep.txt", "nested content")

    dest = output_path.parent / "artifacts" / "sub" / "dir" / "deep.txt"
    assert dest.exists()
    assert dest.read_text() == "nested content"


def test_save_dir(workspace_setup):
    ws = workspace_setup["workspace"]
    ev = workspace_setup["evaluator"]
    output_path = workspace_setup["output_path"]

    # Create a directory with files in the workspace
    (ws / "mydir").mkdir()
    (ws / "mydir" / "a.txt").write_text("aaa")
    (ws / "mydir" / "b.txt").write_text("bbb")

    ev.save_dir("mydir")

    artifacts_dir = output_path.parent / "artifacts" / "mydir"
    assert artifacts_dir.is_dir()
    assert (artifacts_dir / "a.txt").read_text() == "aaa"
    assert (artifacts_dir / "b.txt").read_text() == "bbb"


def test_save_dir_missing(workspace_setup):
    ev = workspace_setup["evaluator"]
    output_path = workspace_setup["output_path"]

    # Should not raise, just log a warning
    ev.save_dir("nonexistent")

    artifacts_dir = output_path.parent / "artifacts" / "nonexistent"
    assert not artifacts_dir.exists()


def test_auto_capture_read_file(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    output_path = tmp_path / "logs" / "reward.json"

    ev = Evaluator(workspace=ws, output_path=output_path, auto_save_artifacts=True)

    (ws / "doc.md").write_text("auto captured content")
    result = ev.read_file("doc.md")

    assert result == "auto captured content"
    dest = output_path.parent / "artifacts" / "doc.md"
    assert dest.exists()
    assert dest.read_text() == "auto captured content"


def test_auto_capture_load_json(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    output_path = tmp_path / "logs" / "reward.json"

    ev = Evaluator(workspace=ws, output_path=output_path, auto_save_artifacts=True)

    (ws / "data.json").write_text(json.dumps({"key": "value"}))
    result = ev.load_json("data.json")

    assert result == {"key": "value"}
    dest = output_path.parent / "artifacts" / "data.json"
    assert dest.exists()
    assert json.loads(dest.read_text()) == {"key": "value"}


def test_auto_capture_disabled_globally(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    output_path = tmp_path / "logs" / "reward.json"

    ev = Evaluator(workspace=ws, output_path=output_path, auto_save_artifacts=False)

    (ws / "doc.md").write_text("should not be captured")
    ev.read_file("doc.md")

    dest = output_path.parent / "artifacts" / "doc.md"
    assert not dest.exists()


def test_per_call_override_save(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    output_path = tmp_path / "logs" / "reward.json"

    # Auto-save OFF globally, but override ON per-call
    ev = Evaluator(workspace=ws, output_path=output_path, auto_save_artifacts=False)

    (ws / "important.md").write_text("save me")
    ev.read_file("important.md", save_artifact=True)

    dest = output_path.parent / "artifacts" / "important.md"
    assert dest.exists()
    assert dest.read_text() == "save me"


def test_per_call_override_skip(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    output_path = tmp_path / "logs" / "reward.json"

    # Auto-save ON globally, but override OFF per-call
    ev = Evaluator(workspace=ws, output_path=output_path, auto_save_artifacts=True)

    (ws / "config.yaml").write_text("skip me")
    ev.read_file("config.yaml", save_artifact=False)

    dest = output_path.parent / "artifacts" / "config.yaml"
    assert not dest.exists()
