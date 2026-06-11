import json

def test_load_json_success(workspace_setup):
    ws = workspace_setup["workspace"]
    ev = workspace_setup["evaluator"]
    
    (ws / "valid.json").write_text(json.dumps({"a": 1}))
    
    data = ev.load_json("valid.json")
    assert data == {"a": 1}

def test_load_json_missing(workspace_setup):
    ev = workspace_setup["evaluator"]
    assert ev.load_json("missing.json") is None

def test_load_json_invalid(workspace_setup):
    ws = workspace_setup["workspace"]
    ev = workspace_setup["evaluator"]
    
    (ws / "invalid.json").write_text("{invalid")
    
    assert ev.load_json("invalid.json") is None

def test_read_file_success(workspace_setup):
    ws = workspace_setup["workspace"]
    ev = workspace_setup["evaluator"]
    
    (ws / "doc.txt").write_text("hello world")
    
    assert ev.read_file("doc.txt") == "hello world"

def test_read_file_missing(workspace_setup):
    ev = workspace_setup["evaluator"]
    assert ev.read_file("missing.txt") is None

def test_file_exists(workspace_setup):
    ws = workspace_setup["workspace"]
    ev = workspace_setup["evaluator"]
    
    assert not ev.file_exists("foo.txt")
    (ws / "foo.txt").write_text("hello")
    assert ev.file_exists("foo.txt")
    
    # directories are not files
    (ws / "bar").mkdir()
    assert not ev.file_exists("bar")

def test_dir_exists(workspace_setup):
    ws = workspace_setup["workspace"]
    ev = workspace_setup["evaluator"]
    
    assert not ev.dir_exists("bar")
    (ws / "bar").mkdir()
    assert ev.dir_exists("bar")
    
    # files are not directories
    (ws / "foo.txt").write_text("hello")
    assert not ev.dir_exists("foo.txt")
