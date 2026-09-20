"""Receipt Autofill application package."""

from .models import PageDefinition, PageEntry
from .storage import AppDataStore

__all__ = ["AppDataStore", "PageDefinition", "PageEntry"]
