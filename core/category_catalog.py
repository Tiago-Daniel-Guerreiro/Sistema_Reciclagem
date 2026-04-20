from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "categorias_catalogo.json"


def _slugify(value: str | None) -> str:
    if not value:
        return ""

    text = value.strip().lower()
    text = (
        text.replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


@lru_cache(maxsize=1)
def _catalog_maps() -> tuple[dict[str, dict], dict[str, str], dict[int, str]]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    known_categories = payload.get("known_categories") or []

    by_key: dict[str, dict] = {}
    alias_to_key: dict[str, str] = {}
    id_to_key: dict[int, str] = {}

    for raw in known_categories:
        category_id = raw.get("id")
        category_key = _slugify(raw.get("key"))
        if category_id is None or not category_key:
            continue
        try:
            category_id_int = int(category_id)
        except (TypeError, ValueError):
            continue

        record = {
            "id": category_id_int,
            "key": category_key,
            "display_name": raw.get("display_name") or category_key,
            "type": raw.get("type") or "outros",
            "eletronico": bool(raw.get("eletronico", False)),
        }
        by_key[category_key] = record
        id_to_key[category_id_int] = category_key

        alias_to_key[category_key] = category_key
        for alias in raw.get("aliases") or []:
            alias_key = _slugify(alias)
            if alias_key:
                alias_to_key[alias_key] = category_key

    return by_key, alias_to_key, id_to_key


def normalize_category_id(raw_category: str | None) -> str:
    token = _slugify(raw_category)
    if not token:
        return "unknown"

    by_key, alias_to_key, id_to_key = _catalog_maps()

    if token.isdigit():
        mapped_key = id_to_key.get(int(token))
        if mapped_key:
            return mapped_key

    canonical = alias_to_key.get(token, token)
    return canonical if canonical in by_key else canonical


def category_metadata(category_id: str | None) -> dict:
    canonical = normalize_category_id(category_id)
    by_key, _, _ = _catalog_maps()

    if canonical in by_key:
        return by_key[canonical]

    pretty = canonical.replace("_", " ").strip().title() or "unspecified_recycling"
    eletronico = any(part in canonical for part in ("eletron", "equip", "lamp", "pilha", "battery"))
    return {
        "id": None,
        "key": canonical,
        "display_name": pretty,
        "type": "eletronico" if eletronico else "outros",
        "eletronico": eletronico,
    }


def get_category_mapping() -> dict[str, str]:
    _, _, id_to_key = _catalog_maps()
    return {str(cat_id): key for cat_id, key in id_to_key.items()}


def known_categories() -> list[dict]:
    by_key, _, _ = _catalog_maps()
    return sorted(by_key.values(), key=lambda item: int(item["id"]))
