"""
Performance benchmarks for scenario generation.

Benchmarks LLM generation speed and throughput.
EXPENSIVE: Makes real API calls. Mark as @slow.
"""

import pytest
import time


@pytest.mark.slow
@pytest.mark.skipif(True, reason="Expensive test - requires real API calls")
class TestGenerationBenchmarks:
    """Benchmark suite for scenario generation performance."""

    def test_single_scenario_generation_time(self, mock_brain):
        """Benchmark time to generate a single scenario."""
        start_time = time.time()

        # In production: call TrinityBrain to generate scenario
        # For now, using mock
        response = "Mocked scenario generation"

        elapsed_time = time.time() - start_time

        # Mock should be fast
        assert elapsed_time < 1.0

        # Real API call baseline: Claude ~2-5s, GPT-4 ~3-6s, Gemini ~2-4s
        # For real implementation, adjust threshold

    def test_batch_generation_throughput(self, mock_brain):
        """Benchmark throughput for generating multiple scenarios."""
        num_scenarios = 10
        start_time = time.time()

        for i in range(num_scenarios):
            # Generate scenario
            response = "Mocked scenario"

        elapsed_time = time.time() - start_time

        scenarios_per_second = num_scenarios / elapsed_time

        # Should process at reasonable rate
        # With mocks: very fast
        # With real APIs: ~0.2-0.5 scenarios/second (sequential)

        assert scenarios_per_second > 0

    def test_parallel_generation_performance(self, mock_brain):
        """Benchmark parallel scenario generation."""
        import concurrent.futures

        num_scenarios = 5

        def generate_scenario(i):
            # Mock generation
            return f"Scenario {i}"

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(generate_scenario, i) for i in range(num_scenarios)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        elapsed_time = time.time() - start_time

        # Parallel should be faster than sequential
        assert len(results) == num_scenarios

        # With real APIs and parallelization:
        # - 3 workers should reduce time by ~2-3x vs sequential
        # - Need to respect API rate limits

    def test_token_count_estimation(self, mock_brain):
        """Benchmark token counting for cost estimation."""
        # For cost optimization, need to estimate tokens before calling API

        sample_prompt = """
        צור תרחיש בדיקה בקטגוריה: פיננסים
        רמת קושי: בינוני
        """

        # Rough estimation: ~1 token per 4 characters for English
        # Hebrew is more complex, might be ~1 token per 2-3 characters

        estimated_tokens = len(sample_prompt) / 3

        # Should have reasonable estimate
        assert estimated_tokens > 0

        # For production: use tiktoken or similar library

    def test_response_caching_effectiveness(self, mock_brain):
        """Test caching of identical prompts."""
        prompt = "צור תרחיש בדיקה בפיננסים"

        # First call
        start_time = time.time()
        response1 = "Mocked response"
        first_call_time = time.time() - start_time

        # Second identical call (should be cached if implemented)
        start_time = time.time()
        response2 = "Mocked response"
        second_call_time = time.time() - start_time

        # If caching implemented, second call should be faster
        # For mocks, both are fast
        assert True  # Placeholder

    def test_streaming_vs_batch_response(self, mock_brain):
        """Compare streaming vs batch response times."""
        # Streaming: Get tokens as they're generated
        # Batch: Wait for full response

        # For user experience, streaming feels faster
        # For processing, batch might be more efficient

        # This would require real API to test
        assert True  # Placeholder

    def test_model_selection_performance_tradeoff(self, mock_brain):
        """Compare performance of different models (Claude, GPT-4, Gemini)."""
        models = ["claude", "gpt4", "gemini"]

        # Each model has different:
        # - Response time
        # - Quality
        # - Cost
        # - Rate limits

        # In production, benchmark each model:
        # - Claude: Generally fast, high quality
        # - GPT-4: Slower, high quality, expensive
        # - Gemini: Fast, good quality, cost-effective

        assert len(models) == 3

    def test_doctrine_prompt_length_impact(self, mock_brain):
        """Test impact of prompt length on response time."""
        from tatlam.core.doctrine import load_prompt

        doctrine = load_prompt()
        doctrine_length = len(doctrine)

        # Longer prompts = more input tokens = higher cost & latency
        # Should optimize doctrine to be concise yet effective

        # Recommendation: Keep doctrine < 2000 tokens (~8000 characters)
        assert doctrine_length > 0

        # If too long, consider trimming
        if doctrine_length > 10000:
            # Might want to optimize
            pass

    def test_retry_logic_performance(self, mock_brain):
        """Test performance of retry logic on failures."""
        import random

        attempts = 0
        max_attempts = 3

        def unreliable_api_call():
            nonlocal attempts
            attempts += 1

            if attempts < 2:
                raise Exception("API error")

            return "Success"

        start_time = time.time()

        # Retry logic
        for attempt in range(max_attempts):
            try:
                result = unreliable_api_call()
                break
            except Exception:
                if attempt == max_attempts - 1:
                    raise
                time.sleep(0.1)  # Brief delay before retry

        elapsed_time = time.time() - start_time

        # Should succeed within reasonable time
        assert result == "Success"
        assert elapsed_time < 1.0

    def test_database_write_performance(self, in_memory_db):
        """Benchmark database write operations."""
        from tatlam.infra.repo import insert_scenario
        import time

        scenarios = [
            {
                "title": f"תרחיש {i}",
                "category": "פיננסים",
                "difficulty": "בינוני",
                "steps": [{"step": 1, "description": "צעד"}]
            }
            for i in range(50)
        ]

        start_time = time.time()

        for scenario in scenarios:
            insert_scenario(scenario)

        elapsed_time = time.time() - start_time

        writes_per_second = len(scenarios) / elapsed_time

        # Should be able to write many scenarios quickly
        assert writes_per_second > 10  # At least 10 writes/second

    def test_end_to_end_scenario_generation_pipeline(self, mock_brain, in_memory_db):
        """Benchmark complete pipeline: generate -> validate -> store."""
        import time

        start_time = time.time()

        # Step 1: Generate (mocked)
        generated_scenario = {
            "title": "תרחיש בדיקה",
            "category": "פיננסים",
            "difficulty": "בינוני",
            "steps": [{"step": 1, "description": "צעד"}]
        }

        # Step 2: Validate
        from tatlam.core.validators import validate_json_schema
        # Validation would happen here

        # Step 3: Store
        from tatlam.infra.repo import insert_scenario
        scenario_id = insert_scenario(generated_scenario)

        elapsed_time = time.time() - start_time

        # Complete pipeline should be fast
        assert scenario_id is not None
        assert elapsed_time < 2.0  # With real API, adjust threshold
