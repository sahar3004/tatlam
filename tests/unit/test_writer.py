from unittest.mock import MagicMock, patch, ANY
import pytest
from tatlam.graph.nodes.writer import writer_node, _get_doctrine_context, _build_generation_prompt, _load_gold_examples
from tatlam.graph.state import SwarmState, WorkflowPhase, ScenarioStatus, ScenarioCandidate
from tatlam.settings import Settings

@pytest.fixture
def mock_settings():
    with patch("tatlam.graph.nodes.writer.get_settings") as mock:
        settings = MagicMock(spec=Settings)
        # Default settings
        settings.WRITER_MODEL_PROVIDER = "openai"
        settings.WRITER_MODEL_NAME = "gpt-4"
        settings.GEN_MODEL = "gpt-3.5"
        settings.LOCAL_MODEL_NAME = "llama-3"
        settings.ANTHROPIC_API_KEY = "key"
        mock.return_value = settings
        yield settings

@pytest.fixture
def mock_clients():
    with patch("tatlam.graph.nodes.writer._get_clients") as mock:
        local = MagicMock()
        cloud = MagicMock()
        anthro = MagicMock()
        mock.return_value = (local, cloud, anthro)
        yield mock, local, cloud, anthro

@pytest.fixture
def mock_pm():
    with patch("tatlam.core.prompts.get_prompt_manager") as mock:
        pm = MagicMock()
        mock.return_value = pm
        pm.get_trinity_prompt.return_value = "System Prompt"
        yield pm

@pytest.fixture
def mock_db():
    with patch("tatlam.infra.db.get_session") as mock_session:
        session = MagicMock()
        mock_session.return_value.__enter__.return_value = session
        yield session

class TestWriterNode:

    def test_get_doctrine_context_edge_cases(self):
        # Surface keywords
        state = SwarmState(category="test surface", batch_size=1)
        # Verify venue logic inside build_prompt
        p = _build_generation_prompt(state)
        assert "טווחי בטיחות" not in p # Allenby specific
        # It should try to load Jaffa doctrine. If mock doctrine not patched, it might fail or return default?
        # _get_doctrine_context imports TRINITY_DOCTRINE.
        # TRINITY_DOCTRINE is a dict.
        # If I want to verify Jaffa path fully, I rely on strings.
        # "כללי ברזל ליפו" is hardcoded in _get_doctrine_context if venue=="jaffa".
        
    def test_writer_node_venue_logic(self, mock_settings, mock_clients, mock_pm):
        """Test venue detection variations."""
        mock_get_clients, _, _, _ = mock_clients
        
        # 1. Surface keyword (English)
        state = SwarmState(category="tachanot-iliyot problem")
        writer_node(state)
        mock_pm.get_trinity_prompt.assert_called()
        assert mock_pm.get_trinity_prompt.call_args[1]["venue"] == "jaffa"
        
        # 2. Suspicious vehicle (Hebrew context mapping)
        state2 = SwarmState(category="רכב חשוד")
        writer_node(state2)
        assert mock_pm.get_trinity_prompt.call_args[1]["context"]["category"] == "suspicious_vehicle"

        # 3. Hebrew Jaffa keyword (hits line 185/357) AND Suspicious Object (hits line 371)
        state3 = SwarmState(category="חפץ חשוד ביפו")
        state3.scout_seeds = ["Seed A"] # Ensure seeds logic in prompt building via writer_node
        writer_node(state3)
        assert mock_pm.get_trinity_prompt.call_args[1]["venue"] == "jaffa"
        assert mock_pm.get_trinity_prompt.call_args[1]["context"]["category"] == "suspicious_object"


    def test_writer_node_strategy_failures(self, mock_settings, mock_clients, mock_pm):
        """Test specific failure blocks."""
        settings = mock_settings
        mock_get_clients, local, cloud, anthro = mock_clients
        
        # 1. Cloud Writer (Strategy 2) fails -> falls to Local (Strategy 3)?
        settings.WRITER_MODEL_PROVIDER = "openai"
        cloud.chat.completions.create.side_effect = Exception("Cloud Fail")
        
        # Local should be called
        local.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content="Local"))]
        
        state = SwarmState(category="test")
        final_state = writer_node(state)
        
        assert final_state.candidates[0].data["_raw_text"] == "Local"
        # check cloud called
        cloud.chat.completions.create.assert_called()
        # check local called
        local.chat.completions.create.assert_called()
        
        # 2. Cloud Fallback (Strategy 4) fails (covered in all_fail, but ensure logs error)
        # If local logic calls local, and it fails.
        # And cloud fallback fails. 
        # Covered in test_writer_node_all_fail partially.
        # But 'all_fail' sets provider=anthropic.
        # Here we set provider=local to force strategy 3 then 4.
        
        settings.WRITER_MODEL_PROVIDER = "local"
        local.chat.completions.create.side_effect = Exception("Local Fail")
        cloud.chat.completions.create.side_effect = Exception("Fallback Fail")
        
        writer_node(SwarmState(category="test"))
        # This covers line 458 logger.error

    def test_load_gold_examples(self, mock_db):
        # Setup mock rows
        mock_db.execute.return_value.fetchall.return_value = [
            ("Title1", "Bg1", "Steps1"),
            ("Title2", None, "Steps2")
        ]
        
        gold = _load_gold_examples("cat")
        assert "### Title1" in gold
        assert "Bg1" in gold
        assert "### Title2" in gold
        
        # Error handling
        mock_db.execute.side_effect = Exception("DB Error")
        assert _load_gold_examples("cat") == ""


    def test_writer_node_strategy_anthropic(self, mock_settings, mock_clients, mock_pm):
        """Test Strategy 1: Anthropic."""
        settings = mock_settings
        settings.WRITER_MODEL_PROVIDER = "anthropic"
        settings.WRITER_MODEL_NAME = "claude-3-opus"
        
        mock_get_clients, local, cloud, anthro = mock_clients
        
        # Anthropic returns content
        anthro_resp = MagicMock()
        anthro_resp.content = [MagicMock(text="Draft Content")]
        anthro.messages.create.return_value = anthro_resp
        
        state = SwarmState(category="test")
        final_state = writer_node(state)
        
        assert final_state.metrics.total_generated == 1
        cand = final_state.candidates[0]
        assert cand.data["_raw_text"] == "Draft Content"
        assert cand.data["_model"] == "claude-3-opus"
        assert cand.status == ScenarioStatus.DRAFT
        
        # Check system prompt call
        anthro.messages.create.assert_called()
        args = anthro.messages.create.call_args[1]
        assert args["system"] == "System Prompt"

    def test_writer_node_strategy_cloud_openai(self, mock_settings, mock_clients, mock_pm):
        """Test Strategy 2: Cloud OpenAI."""
        settings = mock_settings
        settings.WRITER_MODEL_PROVIDER = "openai" # Not anthropic
        
        mock_get_clients, local, cloud, anthro = mock_clients
        # Anthropic disabled via settings or check
        
        # OpenAI returns content
        choice = MagicMock()
        choice.message.content = "GPT Content"
        cloud.chat.completions.create.return_value.choices = [choice]
        
        state = SwarmState(category="test")
        final_state = writer_node(state)
        
        assert final_state.candidates[0].data["_raw_text"] == "GPT Content"
        cloud.chat.completions.create.assert_called()

    def test_writer_node_strategy_local(self, mock_settings, mock_clients, mock_pm):
        """Test Strategy 3: Local LLM."""
        settings = mock_settings
        settings.WRITER_MODEL_PROVIDER = "local" # Prefer local? 
        # Actually code logic:
        # 1. if anthropic...
        # 2. if not draft and use_cloud_first and cloud ...
        # 3. if not draft and local ...
        
        # To hit local primary/fallback:
        # Either provider=local (so use_cloud_first is False)
        # Or cloud failed/missing.
        
        mock_get_clients, local, cloud, anthro = mock_clients
        
        # Case A: Provider=local
        settings.WRITER_MODEL_PROVIDER = "local" 
        # use_cloud_first will be False
        
        choice = MagicMock()
        choice.message.content = "Local Content"
        local.chat.completions.create.return_value.choices = [choice]
        
        state = SwarmState(category="test")
        final_state = writer_node(state)
        
        assert final_state.candidates[0].data["_raw_text"] == "Local Content"
        local.chat.completions.create.assert_called()
        cloud.chat.completions.create.assert_not_called()

    def test_writer_node_strategy_fallback_cloud(self, mock_settings, mock_clients, mock_pm):
        """Test Strategy 4: Cloud Fallback (when local fails)."""
        settings = mock_settings
        settings.WRITER_MODEL_PROVIDER = "local"
        
        mock_get_clients, local, cloud, anthro = mock_clients
        
        # Local fails
        local.chat.completions.create.side_effect = Exception("Local Down")
        
        # Cloud succeeds
        choice = MagicMock()
        choice.message.content = "Fallback Content"
        cloud.chat.completions.create.return_value.choices = [choice]
        
        state = SwarmState(category="test")
        final_state = writer_node(state)
        
        assert final_state.candidates[0].data["_raw_text"] == "Fallback Content"
        # Metric incremented for error
        assert final_state.metrics.llm_errors == 1

    def test_writer_node_all_fail(self, mock_settings, mock_clients, mock_pm):
        """Test all strategies failure."""
        settings = mock_settings
        settings.WRITER_MODEL_PROVIDER = "anthropic"
        
        mock_get_clients, local, cloud, anthro = mock_clients
        
        # All fail
        anthro.messages.create.side_effect = Exception("Anthropic Fail")
        cloud.chat.completions.create.side_effect = Exception("Cloud Fail") # fallback?
        # Logic:
        # 1. Anthropic -> fail
        # 2. Cloud OpenAI (Strategy 2) -> also fail
        # 3. Local (Strategy 3) -> fail (if available)
        
        local.chat.completions.create.side_effect = Exception("Local Fail")
        
        state = SwarmState(category="test")
        final_state = writer_node(state)
        
        assert not final_state.candidates
        assert "Writer failed" in final_state.errors[0]
        assert final_state.metrics.llm_errors >= 2 

    def test_writer_node_repair_logic(self, mock_settings, mock_clients, mock_pm):
        """Test repair critique logic."""
        mock_get_clients, local, cloud, anthro = mock_clients
        cloud.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content="Repaired"))]
        
        state = SwarmState(category="test")
        
        # Scenario needing repair
        busted = ScenarioCandidate(data={"title": "Bad"}, status=ScenarioStatus.REJECTED)
        busted.critique = "Too vague"
        busted.attempt_count = 1
        state.candidates.append(busted)
        state.max_retries_per_scenario = 2
        
        writer_node(state)
        
        # Verify prompt construction called with repair
        # We can't easily check internal function call args unless we mock _build_generation_prompt
        # But we tested build_prompt separately.
        # We can verify it runs without error.
        assert state.candidates[-1].data["_raw_text"] == "Repaired"

    def test_writer_node_gold_loading(self, mock_settings, mock_clients, mock_pm):
        """Test gold loading trigger."""
        mock_get_clients, local, cloud, anthro = mock_clients
        cloud.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content="Draft"))]
        
        with patch("tatlam.graph.nodes.writer._load_gold_examples") as mock_load:
            mock_load.return_value = "Loaded Gold"
            
            state = SwarmState(category="test")
            # First run - loads gold
            writer_node(state)
            mock_load.assert_called_once()
            assert state.gold_examples == "Loaded Gold"
            
            # Second run - already loaded
            mock_load.reset_mock()
            writer_node(state)
            mock_load.assert_not_called()

    def test_get_clients_helper(self):
        """Test _get_clients logic."""
        from tatlam.graph.nodes.writer import _get_clients
        
        with patch("tatlam.core.llm_factory.client_local") as mk_local, \
             patch("tatlam.core.llm_factory.client_cloud") as mk_cloud, \
             patch("tatlam.core.llm_factory.create_writer_client") as mk_writer:
             
             mk_local.return_value = "local"
             mk_cloud.return_value = "cloud"
             mk_writer.return_value = "anthro"
             
             l, c, a = _get_clients()
             assert l == "local"
             assert c == "cloud"
             assert a == "anthro"
             
             # Failures
             mk_local.side_effect = Exception("err")
             mk_cloud.side_effect = Exception("err")
             mk_writer.side_effect = Exception("err")
             
             l, c, a = _get_clients()
             assert l is None
             assert c is None
             assert a is None
