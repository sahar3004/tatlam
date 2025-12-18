from __future__ import annotations

from flask import Blueprint

from .v1 import bp as v1_bp, category, create_scenario, scenario_one, scenarios


def make_legacy_api_bp() -> Blueprint:
    legacy = Blueprint("api_legacy", __name__, url_prefix="/api")
    legacy.add_url_rule("/scenarios", view_func=scenarios, methods=["GET"])  # GET list
    legacy.add_url_rule("/scenarios", view_func=create_scenario, methods=["POST"])  # create
    legacy.add_url_rule("/scenario/<int:sid>", view_func=scenario_one)
    legacy.add_url_rule("/cat/<slug>.json", view_func=category)
    return legacy


__all__ = ["v1_bp", "make_legacy_api_bp"]
