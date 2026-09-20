from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import PageDefinition


class AppDataStore:
    def __init__(self, file_path: str | Path | None = None) -> None:
        default_dir = Path(os.getenv("LOCALAPPDATA", Path.home())).joinpath("ReceiptAutofill")
        self.file_path = Path(file_path) if file_path else default_dir / "pages.json"
        self.settings_file_path = self.file_path.with_name("settings.json")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load_pages(self) -> list[PageDefinition]:
        if not self.file_path.exists():
            return []

        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        if isinstance(raw, dict):
            raw = raw.get("pages", [])

        if not isinstance(raw, list):
            return []

        pages: list[PageDefinition] = []
        for item in raw:
            if isinstance(item, dict):
                pages.append(PageDefinition.from_dict(item))
        return pages

    def save_pages(self, pages: list[PageDefinition]) -> None:
        payload = [page.to_dict() for page in pages]
        self.file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_last_url(self) -> str:
        if not self.settings_file_path.exists():
            return ""

        try:
            raw = json.loads(self.settings_file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return ""

        if isinstance(raw, dict):
            return str(raw.get("last_url", ""))
        return ""

    def save_last_url(self, url: str) -> None:
        payload = {"last_url": str(url or "")}
        self.settings_file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def clear_pages(self) -> None:
        self.save_pages([])
