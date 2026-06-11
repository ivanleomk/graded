import json
import pytest

def test_criterion_duplicate_name_rejected(workspace_setup):
    ev = workspace_setup["evaluator"]
    
    @ev.criterion("same_name")
    def check_a(ws):
        return True
    
    with pytest.raises(ValueError, match="Duplicate criterion name: 'same_name'"):
        @ev.criterion("same_name")
        def check_b(ws):
            return True

def test_criterion_registration(workspace_setup):
    ev = workspace_setup["evaluator"]
    
    @ev.criterion("check_1", weight=2.5)
    def my_check(ws):
        return True
        
    assert len(ev.criteria) == 1
    assert ev.criteria[0]["name"] == "check_1"
    assert ev.criteria[0]["weight"] == 2.5
    assert ev.criteria[0]["func"] == my_check
    assert ev.criteria[0]["fatal"] == False

def test_run_weighted_scoring(workspace_setup):
    ev = workspace_setup["evaluator"]
    output_path = workspace_setup["output_path"]
    
    @ev.criterion("check_true", weight=3.0)
    def check_true(ws):
        return True
        
    @ev.criterion("check_false", weight=1.0)
    def check_false(ws):
        return False
        
    @ev.criterion("check_float", weight=2.0)
    def check_float(ws):
        return 0.5
        
    ev.run()
    
    # Total weight = 3.0 + 1.0 + 2.0 = 6.0
    # Weighted score = 1.0 * 3.0 + 0.0 * 1.0 + 0.5 * 2.0 = 4.0
    # Expected reward = 4.0 / 6.0 = 0.6667
    
    assert output_path.exists()
    reward_data = json.loads(output_path.read_text())
    reward_data["reward"] = round(reward_data["reward"], 4)
    assert reward_data == {
        "reward": 0.6667,
        "check_true": 1.0,
        "check_false": 0.0,
        "check_float": 0.5
    }

def test_run_handles_exceptions(workspace_setup):
    ev = workspace_setup["evaluator"]
    output_path = workspace_setup["output_path"]
    
    @ev.criterion("check_pass", weight=1.0)
    def check_pass(ws):
        return True
        
    @ev.criterion("check_crash", weight=1.0)
    def check_crash(ws):
        raise ValueError("Simulated crash")
        
    ev.run()
    
    # Total weight = 2.0
    # Weighted score = 1.0 * 1.0 + 0.0 * 1.0 = 1.0
    # Expected reward = 1.0 / 2.0 = 0.5
    
    reward_data = json.loads(output_path.read_text())
    assert reward_data == {
        "reward": 0.5,
        "check_pass": 1.0,
        "check_crash": 0.0
    }

def test_fatal_criterion_fails(workspace_setup):
    ev = workspace_setup["evaluator"]
    output_path = workspace_setup["output_path"]
    
    @ev.criterion("file_check", weight=0.10, fatal=True)
    def check_file(ws):
        return False
    
    @ev.criterion("content_check", weight=0.90)
    def check_content(ws):
        return 1.0
    
    ev.run()
    
    reward_data = json.loads(output_path.read_text())
    # Fatal criterion failed -> reward is 0.0, content_check never ran
    assert reward_data["reward"] == 0.0
    assert "content_check" not in reward_data

def test_fatal_criterion_passes(workspace_setup):
    ev = workspace_setup["evaluator"]
    output_path = workspace_setup["output_path"]
    
    @ev.criterion("file_check", weight=1.0, fatal=True)
    def check_file(ws):
        return True
    
    @ev.criterion("content_check", weight=1.0)
    def check_content(ws):
        return 0.8
    
    ev.run()
    
    reward_data = json.loads(output_path.read_text())
    # Fatal criterion passed -> normal scoring continues
    # (1.0 * 1.0 + 0.8 * 1.0) / 2.0 = 0.9
    assert reward_data["reward"] == 0.9
    assert reward_data == {"reward": 0.9, "file_check": 1.0, "content_check": 0.8}
