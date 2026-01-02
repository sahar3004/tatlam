"""
Tests for tatlam.core.rules - RuleEngine and Rule classes.
"""

import tempfile
import yaml
from pathlib import Path

from tatlam.core.rules import Rule, RuleEngine


class TestRule:
    """Tests for the Rule dataclass."""

    def test_rule_creation(self):
        """Test basic rule creation with all fields."""
        rule = Rule(
            id="test-001",
            category="safety",
            content="תמיד לבדוק סביבה לפני פעולה",
            context={"venue": "allenby"},
            source="test",
        )
        assert rule.id == "test-001"
        assert rule.category == "safety"
        assert rule.content == "תמיד לבדוק סביבה לפני פעולה"
        assert rule.context == {"venue": "allenby"}
        assert rule.source == "test"

    def test_rule_creation_defaults(self):
        """Test rule creation with default values."""
        rule = Rule(id="test-002", category="general", content="כלל כללי")
        assert rule.context == {}
        assert rule.source == "core"

    def test_is_applicable_no_context_requirement(self):
        """Rule with no context requirements should always be applicable."""
        rule = Rule(id="r1", category="general", content="Always apply")
        assert rule.is_applicable({}) is True
        assert rule.is_applicable({"venue": "jaffa"}) is True
        assert rule.is_applicable({"random": "value"}) is True

    def test_is_applicable_matching_context(self):
        """Rule with matching context should be applicable."""
        rule = Rule(
            id="r2",
            category="location",
            content="Surface rule",
            context={"location_type": "surface"},
        )
        assert rule.is_applicable({"location_type": "surface"}) is True
        assert rule.is_applicable({"location_type": "surface", "extra": "value"}) is True

    def test_is_applicable_non_matching_context(self):
        """Rule with non-matching context should not be applicable."""
        rule = Rule(
            id="r3",
            category="location",
            content="Underground rule",
            context={"location_type": "underground"},
        )
        assert rule.is_applicable({"location_type": "surface"}) is False
        assert rule.is_applicable({}) is False

    def test_is_applicable_list_context(self):
        """Rule with list context should match if value is in list."""
        rule = Rule(
            id="r4",
            category="category",
            content="Multi-category rule",
            context={"category": ["suspicious_object", "violence"]},
        )
        assert rule.is_applicable({"category": "suspicious_object"}) is True
        assert rule.is_applicable({"category": "violence"}) is True
        assert rule.is_applicable({"category": "other"}) is False

    def test_is_applicable_multiple_requirements(self):
        """Rule with multiple context requirements - all must match."""
        rule = Rule(
            id="r5",
            category="complex",
            content="Complex rule",
            context={"venue": "jaffa", "risk_level": "high"},
        )
        assert rule.is_applicable({"venue": "jaffa", "risk_level": "high"}) is True
        assert rule.is_applicable({"venue": "jaffa", "risk_level": "low"}) is False
        assert rule.is_applicable({"venue": "jaffa"}) is False


class TestRuleEngine:
    """Tests for the RuleEngine class."""

    def test_engine_creation_missing_path(self):
        """Engine should handle missing knowledge base path gracefully."""
        engine = RuleEngine(knowledge_base_path="/nonexistent/path")
        assert engine.rules == []

    def test_engine_load_rules_from_yaml(self):
        """Engine should load rules from YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test YAML file
            yaml_content = {
                "rules": [
                    {"id": "test-1", "category": "safety", "content": "Safety rule 1"},
                    {
                        "id": "test-2",
                        "category": "procedure",
                        "content": "Procedure rule 1",
                        "context": {"venue": "allenby"},
                    },
                ]
            }
            yaml_path = Path(tmpdir) / "test.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f, allow_unicode=True)

            engine = RuleEngine(knowledge_base_path=tmpdir)
            assert len(engine.rules) == 2
            assert engine.rules[0].id == "test-1"
            assert engine.rules[1].context == {"venue": "allenby"}

    def test_engine_load_nested_yaml_files(self):
        """Engine should recursively load YAML files from subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = Path(tmpdir) / "domains"
            subdir.mkdir()

            yaml_content = {
                "rules": [{"id": "nested-1", "category": "domain", "content": "Nested rule"}]
            }
            yaml_path = subdir / "domain.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f, allow_unicode=True)

            engine = RuleEngine(knowledge_base_path=tmpdir)
            assert len(engine.rules) == 1
            assert engine.rules[0].id == "nested-1"
            assert engine.rules[0].source == "domain"

    def test_engine_handles_invalid_yaml(self):
        """Engine should handle invalid YAML files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an invalid YAML file
            yaml_path = Path(tmpdir) / "invalid.yaml"
            with open(yaml_path, "w") as f:
                f.write("this: is: not: valid: yaml: {{{{")

            engine = RuleEngine(knowledge_base_path=tmpdir)
            # Should not crash, just log error
            assert engine.rules == []

    def test_engine_handles_missing_required_fields(self):
        """Engine should skip rules missing required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_content = {
                "rules": [
                    {"category": "test", "content": "Missing id"},  # Missing 'id'
                    {"id": "valid", "category": "test", "content": "Valid rule"},
                ]
            }
            yaml_path = Path(tmpdir) / "partial.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f, allow_unicode=True)

            engine = RuleEngine(knowledge_base_path=tmpdir)
            assert len(engine.rules) == 1
            assert engine.rules[0].id == "valid"

    def test_get_rules_filters_by_context(self):
        """get_rules should return only applicable rules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_content = {
                "rules": [
                    {"id": "r1", "category": "general", "content": "General rule"},
                    {
                        "id": "r2",
                        "category": "surface",
                        "content": "Surface only",
                        "context": {"location_type": "surface"},
                    },
                    {
                        "id": "r3",
                        "category": "underground",
                        "content": "Underground only",
                        "context": {"location_type": "underground"},
                    },
                ]
            }
            yaml_path = Path(tmpdir) / "test.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f, allow_unicode=True)

            engine = RuleEngine(knowledge_base_path=tmpdir)

            # Should get general + surface rules
            surface_rules = engine.get_rules({"location_type": "surface"})
            assert len(surface_rules) == 2
            rule_ids = [r.id for r in surface_rules]
            assert "r1" in rule_ids
            assert "r2" in rule_ids
            assert "r3" not in rule_ids

    def test_format_rules_for_prompt(self):
        """format_rules_for_prompt should return formatted string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_content = {
                "rules": [
                    {"id": "r1", "category": "safety", "content": "Safety content 1"},
                    {"id": "r2", "category": "safety", "content": "Safety content 2"},
                    {"id": "r3", "category": "procedure", "content": "Procedure content"},
                ]
            }
            yaml_path = Path(tmpdir) / "test.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f, allow_unicode=True)

            engine = RuleEngine(knowledge_base_path=tmpdir)
            formatted = engine.format_rules_for_prompt({})

            assert "### SAFETY" in formatted
            assert "### PROCEDURE" in formatted
            assert "- Safety content 1" in formatted
            assert "- Procedure content" in formatted

    def test_format_rules_empty_when_no_applicable(self):
        """format_rules_for_prompt should return empty string when no rules apply."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_content = {
                "rules": [
                    {
                        "id": "r1",
                        "category": "surface",
                        "content": "Surface only",
                        "context": {"location_type": "surface"},
                    }
                ]
            }
            yaml_path = Path(tmpdir) / "test.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f, allow_unicode=True)

            engine = RuleEngine(knowledge_base_path=tmpdir)
            formatted = engine.format_rules_for_prompt({"location_type": "underground"})
            assert formatted == ""

    def test_reload_rules(self):
        """reload should refresh rules from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "test.yaml"

            # Initial content
            yaml_content = {"rules": [{"id": "r1", "category": "test", "content": "Initial"}]}
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f, allow_unicode=True)

            engine = RuleEngine(knowledge_base_path=tmpdir)
            assert len(engine.rules) == 1
            assert engine.rules[0].content == "Initial"

            # Update content
            yaml_content = {
                "rules": [
                    {"id": "r1", "category": "test", "content": "Updated"},
                    {"id": "r2", "category": "test", "content": "New rule"},
                ]
            }
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f, allow_unicode=True)

            engine.reload()
            assert len(engine.rules) == 2
            assert engine.rules[0].content == "Updated"

    def test_handles_yaml_without_rules_key(self):
        """Engine should handle YAML files without 'rules' key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_content = {"metadata": {"version": "1.0"}}
            yaml_path = Path(tmpdir) / "meta.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f, allow_unicode=True)

            engine = RuleEngine(knowledge_base_path=tmpdir)
            assert engine.rules == []
