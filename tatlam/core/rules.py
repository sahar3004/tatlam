import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """
    Represents a single knowledge rule or constraint.
    """

    id: str
    category: str
    content: str
    context: Dict[str, Any] = field(default_factory=dict)
    source: str = "core"

    def is_applicable(self, context: Dict[str, Any]) -> bool:
        """
        Checks if the rule is applicable based on the provided context.
        If the rule has no context requirements, it is always applicable.
        If it has requirements, ALL must be met by the provided context.
        """
        if not self.context:
            return True

        for key, required_value in self.context.items():
            if key not in context:
                return False
            # Handle list requirements (if context value is in list of allowed values)
            if isinstance(required_value, list):
                if context[key] not in required_value:
                    return False
            elif context[key] != required_value:
                return False
        return True


class RuleEngine:
    """
    Manages the loading, indexing, and retrieval of rules from the knowledge base.
    """

    def __init__(self, knowledge_base_path: str = "tatlam/knowledge/rules"):
        # Resolve path relative to the project root if needed
        self.kb_path = Path(knowledge_base_path)
        if not self.kb_path.is_absolute():
            # Assuming run from project root
            self.kb_path = Path.cwd() / knowledge_base_path

        self.rules: List[Rule] = []
        self._load_rules()

    def _load_rules(self):
        """
        Recursively loads all .yaml files from the knowledge base directory.
        """
        if not self.kb_path.exists():
            logger.warning(f"Knowledge base path not found: {self.kb_path}")
            return

        for yaml_file in self.kb_path.rglob("*.yaml"):
            try:
                self._load_file(yaml_file)
            except Exception as e:
                logger.error(f"Failed to load rules from {yaml_file}: {e}")

    def _load_file(self, file_path: Path):
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "rules" not in data:
            return

        source_name = file_path.stem
        for item in data["rules"]:
            try:
                rule = Rule(
                    id=item["id"],
                    category=item.get("category", "general"),
                    content=item["content"],
                    context=item.get("context", {}),
                    source=source_name,
                )
                self.rules.append(rule)
            except KeyError as e:
                logger.error(f"Missing required field in rule in {file_path}: {e}")

    def get_rules(self, context: Dict[str, Any]) -> List[Rule]:
        """
        Returns all rules applicable to the given context.
        Context example: {'location_type': 'surface', 'category': 'chafetz_hashud'}
        """
        return [rule for rule in self.rules if rule.is_applicable(context)]

    def format_rules_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Returns a formatted string of rules for injection into the System Prompt.
        Groups rules by category.
        """
        applicable_rules = self.get_rules(context)
        if not applicable_rules:
            return ""

        # Group by category
        grouped = {}
        for rule in applicable_rules:
            if rule.category not in grouped:
                grouped[rule.category] = []
            grouped[rule.category].append(rule.content)

        output = []
        for category, contents in grouped.items():
            output.append(f"### {category.upper().replace('_', ' ')}")
            for content in contents:
                output.append(f"- {content}")
            output.append("")

        return "\n".join(output).strip()

    def reload(self):
        """Force reload of all rules from disk."""
        self.rules = []
        self._load_rules()
