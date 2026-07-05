from __future__ import annotations

import os
from collections.abc import Iterable


def redact_env_secret_values(text: str, keys: Iterable[str]) -> str:
    redacted = text
    for key in keys:
        value = os.environ.get(key)
        if value:
            redacted = redacted.replace(value, f"<redacted:{key}>")
    return redacted
