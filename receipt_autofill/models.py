from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class PageEntry:
    selector: str = ""
    text: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"selector": self.selector, "text": self.text}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PageEntry":
        return cls(selector=str(data.get("selector", "")), text=str(data.get("text", "")))

    def is_valid(self) -> bool:
        return bool(self.selector.strip())


@dataclass
class PageDefinition:
    name: str = ""
    entries: list[PageEntry] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))

    def is_valid(self) -> bool:
        return bool(self.name.strip())

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "entries": [entry.to_dict() for entry in self.entries]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PageDefinition":
        page_id = str(data.get("id") or uuid4())
        entries = [PageEntry.from_dict(item) for item in data.get("entries", [])]
        return cls(id=page_id, name=str(data.get("name", "")), entries=entries)
