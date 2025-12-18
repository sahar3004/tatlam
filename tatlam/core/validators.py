from __future__ import annotations

import json
from typing import Any


def build_validator_prompt(bundle: dict[str, Any]) -> str:
    return (
        "אתה ולידטור JSON קפדני. בדוק ותקן את המבנה במידת הצורך. "
        "החזר אך ורק JSON תקין – ללא הסברים/גדרות קוד. "
        "שמור על העברית בדיוק כפי שהיא.\n\n" + json.dumps(bundle, ensure_ascii=False)
    )


__all__ = ["build_validator_prompt"]
