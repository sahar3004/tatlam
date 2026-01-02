import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from tatlam.graph.workflow import (
    create_scenario_graph,
    run_scenario_generation,
    run_scenario_generation_async,
    WorkflowPhase,
    SwarmState
)

@pytest.fixture
def mock_langgraph():
    # Create mock module structure
    mock_graph_module = MagicMock()
    mock_state_graph = MagicMock()
    mock_graph_module.StateGraph = mock_state_graph
    mock_graph_module.END = "END"
    
    mock_builder = MagicMock()
    mock_state_graph.return_value = mock_builder
    mock_compiled = MagicMock()
    mock_builder.compile.return_value = mock_compiled

    # Patch sys.modules to effectively "install" langgraph
    with patch.dict("sys.modules", {
        "langgraph": MagicMock(),
        "langgraph.graph": mock_graph_module
    }):
        yield mock_state_graph, mock_builder, mock_compiled

@pytest.fixture
def mock_end(mock_langgraph):
    # This is implicit in the mock_langgraph fixture now, but we can return the value
    return "END"


def test_create_scenario_graph_structure(mock_langgraph, mock_end):
    """Test that the graph is built with correct nodes and edges."""
    mock_class, mock_builder, mock_compiled = mock_langgraph

    graph = create_scenario_graph()

    # Verify StateGraph instantiated with correct state type
    mock_class.assert_called_once_with(SwarmState)
    
    # Verify nodes added
    expected_nodes = [
        "init", "scout", "curator", "writer", "clerk", 
        "deduplicator", "judge", "supervisor", "archivist"
    ]
    for node in expected_nodes:
        # Check if add_node was called with this node name
        # We check specific calls because order matters somewhat but existence is key
        calls = [c for c in mock_builder.add_node.call_args_list if c[0][0] == node]
        assert calls, f"Node {node} was not added"

    # Verify linear edges
    mock_builder.set_entry_point.assert_called_once_with("init")
    mock_builder.add_edge.assert_any_call("init", "scout")
    mock_builder.add_edge.assert_any_call("scout", "curator")
    mock_builder.add_edge.assert_any_call("curator", "writer")
    mock_builder.add_edge.assert_any_call("writer", "clerk")
    mock_builder.add_edge.assert_any_call("clerk", "deduplicator")
    mock_builder.add_edge.assert_any_call("deduplicator", "judge")
    mock_builder.add_edge.assert_any_call("judge", "supervisor")
    mock_builder.add_edge.assert_any_call("archivist", "END") # END matches our mock

    # Verify conditional edges
    mock_builder.add_conditional_edges.assert_called_once()
    args = mock_builder.add_conditional_edges.call_args[0]
    assert args[0] == "supervisor"
    # args[1] is the function (should_continue)
    assert callable(args[1])
    # args[2] is the map
    assert args[2] == {
        "writer": "writer",
        "archivist": "archivist",
        "end": "END",
    }

    assert graph == mock_compiled

def test_create_scenario_graph_no_langgraph():
    """Test ImportError when langgraph is missing."""
    # We need to simulate ImportError when importing langgraph.graph
    # Since we can't easily uninstall the package, we use patch.dict to remove it from sys.modules
    # AND wrap the import using side_effect if possible, OR just ensure it's not found.
    # But if real library exists, simple removal from sys.modules might just trigger reload.
    
    # Best generic way for this codebase:
    with patch.dict("sys.modules", {"langgraph": None, "langgraph.graph": None}):
        with pytest.raises(ImportError, match="langgraph is required"):
             create_scenario_graph()


@pytest.fixture
def anyio_backend():
    return "asyncio"

def test_run_scenario_generation_success(mock_langgraph):
    """Test successful synchronous execution."""
    mock_class, mock_builder, mock_compiled = mock_langgraph
    
    # Mock invoke returning a state
    final_state = SwarmState(category="test")
    final_state.log_phase_change(WorkflowPhase.COMPLETE)
    mock_compiled.invoke.return_value = final_state

    result = run_scenario_generation("test_cat")
    
    mock_compiled.invoke.assert_called_once()
    assert result == final_state
    assert result.current_phase == WorkflowPhase.COMPLETE


def test_run_scenario_generation_failure(mock_langgraph):
    """Test exception handling in synchronous execution."""
    mock_class, mock_builder, mock_compiled = mock_langgraph
    
    mock_compiled.invoke.side_effect = Exception("Graph Error")

    result = run_scenario_generation("test_cat")
    
    assert result.errors
    assert "Graph Error" in result.errors[0]
    assert result.current_phase == WorkflowPhase.ERROR

@pytest.mark.anyio
async def test_run_scenario_generation_async_success(mock_langgraph):
    """Test successful asynchronous execution."""
    mock_class, mock_builder, mock_compiled = mock_langgraph
    
    # Mock ainvoke
    final_state = SwarmState(category="test")
    # Need to make return_value waitable or use AsyncMock
    mock_compiled.ainvoke = AsyncMock(return_value=final_state)

    result = await run_scenario_generation_async("test_cat")
    
    mock_compiled.ainvoke.assert_called_once()
    assert result == final_state

@pytest.mark.anyio
async def test_run_scenario_generation_async_failure(mock_langgraph):
    """Test exception handling in async execution."""
    mock_class, mock_builder, mock_compiled = mock_langgraph
    
    mock_compiled.ainvoke = AsyncMock(side_effect=Exception("Async Error"))

    result = await run_scenario_generation_async("test_cat")
    
    assert result.errors
    assert "Async Error" in result.errors[0]
    assert result.current_phase == WorkflowPhase.ERROR
