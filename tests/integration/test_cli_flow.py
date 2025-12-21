"""
Integration test for CLI command flow.
Verifies that CLI arguments are correctly parsed and passed to the logic layer.
"""
import sys
import pytest
from unittest.mock import MagicMock, patch

# Mock batch_logic before importing CLI to handle the inner import
mock_logic_module = MagicMock()
sys.modules["tatlam.core.batch_logic"] = mock_logic_module

from tatlam.cli import batch_cmd

def test_batch_cmd_happy_path():
    """Test standard batch command execution."""
    test_args = ["batch_cmd.py", "--category", "TestCat", "--owner", "Tester"]
    
    # Setup mock return value
    mock_logic_module.run_batch.return_value = {
        "bundle_id": "test_bundle_123",
        "scenarios": [1, 2, 3]
    }
    
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as e:
            batch_cmd.main()
        
        assert e.value.code == 0
        
    # Verify logic call
    mock_logic_module.run_batch.assert_called_once()
    call_args = mock_logic_module.run_batch.call_args
    assert call_args[0][0] == "TestCat"  # positional arg 'category'
    assert call_args[1]["owner"] == "Tester"

def test_batch_cmd_async_flag():
    """Test that --async flag triggers the async runner."""
    test_args = ["batch_cmd.py", "--category", "AsyncCat", "--async"]
    
    mock_logic_module.run_batch_async.return_value = {"scenarios": []}
    
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as e:
            batch_cmd.main()
            
    # Verify async runner called
    mock_logic_module.run_batch_async.assert_called_once()
    
def test_batch_cmd_missing_arg():
    """Test error handling for missing required args."""
    test_args = ["batch_cmd.py"] # Missing category
    
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as e:
            # argparse calls sys.exit(2) on error
            batch_cmd.main()
        
        assert e.value.code != 0

