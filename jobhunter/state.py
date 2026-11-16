"""מצב: seen.json = {job_id: first_seen_iso}. מנקה רשומות ישנות מ-45 יום."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

from . import config


def load(path: Path) -> Dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def prune(state: Dict[str, str], now: datetime = None) -> Dict[str, str]:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=config.STATE_MAX_AGE_DAYS)
    out = {}
    for k, v in state.items():
        try:
            if datetime.fromisoformat(v) >= cutoff:
                out[k] = v
        except (ValueError, TypeError):
            out[k] = now.isoformat(timespec="seconds")
    return out


def save(path: Path, state: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(sorted(state.items())), f, ensure_ascii=False, indent=0)
        f.write("\n")
