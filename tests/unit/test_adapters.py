
import pytest
from unittest.mock import MagicMock
from tatlam.core.adapters import (
    WriterFallbackAdapter,
    JudgeFallbackAdapter,
    SimulatorFallbackAdapter,
    LocalAsWriterAdapter,
    LocalAsJudgeAdapter,
    LocalAsSimulatorAdapter,
    _DictToObj
)

class TestAdapters:
    
    def test_writer_fallback_success(self):
        primary = MagicMock()
        primary.messages.stream.return_value = "success"
        fallback = MagicMock()
        
        adapter = WriterFallbackAdapter(primary, fallback)
        assert adapter.messages.stream() == "success"
        fallback.messages.stream.assert_not_called()

    def test_writer_fallback_failure(self):
        primary = MagicMock()
        primary.messages.stream.side_effect = Exception("error")
        fallback = MagicMock()
        fallback.messages.stream.return_value = "fallback"
        
        adapter = WriterFallbackAdapter(primary, fallback)
        assert adapter.messages.stream() == "fallback"
        primary.messages.stream.assert_called()
        fallback.messages.stream.assert_called()

    def test_judge_fallback_failure(self):
        primary = MagicMock()
        primary.generate_content.side_effect = Exception("error")
        fallback = MagicMock()
        fallback.generate_content.return_value = "fallback"
        
        adapter = JudgeFallbackAdapter(primary, fallback)
        assert adapter.generate_content("prompt") == "fallback"

    def test_simulator_fallback_failure(self):
        primary = MagicMock()
        primary.chat.completions.create.side_effect = Exception("error")
        fallback = MagicMock()
        fallback.chat.completions.create.return_value = "fallback"
        
        adapter = SimulatorFallbackAdapter(primary, fallback)
        assert adapter.chat.completions.create() == "fallback"

    def test_dict_to_obj(self):
        d = {"a": 1, "b": {"c": 2}, "d": [{"e": 3}]}
        obj = _DictToObj(d)
        assert obj.a == 1
        assert obj.b.c == 2
        assert obj.d[0].e == 3
        # Attribute access for missing key returns None
        assert obj.x is None

    def test_local_as_judge(self):
        provider = MagicMock()
        provider.generate.return_value = "content"
        adapter = LocalAsJudgeAdapter(provider)
        res = adapter.generate_content("prompt")
        assert res.text == "content"
        provider.generate.assert_called_with("prompt")

    def test_local_as_write(self):
        provider = MagicMock()
        provider.create_chat_completion.return_value = [{"choices": [{"delta": {"content": "chunk"}}]}]
        
        adapter = LocalAsWriterAdapter(provider)
        with adapter.messages.stream([{"role": "user", "content": "hi"}]) as stream:
             chunks = list(stream.text_stream)
             assert chunks == ["chunk"]
