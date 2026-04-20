from __future__ import annotations
import json
import os
import re
from datetime import datetime, timezone
from html import unescape
from tempfile import NamedTemporaryFile

def now_iso() -> str:
	return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def atomic_write_json(file_path: str, payload: dict | list) -> None:
	directory = os.path.dirname(file_path)
	os.makedirs(directory, exist_ok=True)

	with NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as temp_file:
		json.dump(payload, temp_file, ensure_ascii=False, indent=2)
		temp_path = temp_file.name

	os.replace(temp_path, file_path)

def normalize_text(value: str | None, remove_accents: bool = True) -> str:
	if not value:
		return ""
	
	text = unescape(value).strip().lower()
	text = re.sub(r"\s+", " ", text)
	
	if remove_accents:
		text = remove_diacritics(text)
	
	return text

def remove_diacritics(text: str) -> str:
	replacements = {
		"á": "a", "à": "a", "â": "a", "ã": "a",
		"é": "e", "ê": "e",
		"í": "i",
		"ó": "o", "ô": "o", "õ": "o",
		"ú": "u",
		"ç": "c",
	}
	for old, new in replacements.items():
		text = text.replace(old, new)
	return text

def normalize_token(value: str | None) -> str:
	if not value:
		return ""
	
	token = normalize_text(value, remove_accents=True)
	token = token.replace("-", "_").replace(" ", "_")
	while "__" in token:
		token = token.replace("__", "_")
	return token.strip("_")

def slugify(value: str | None) -> str:
	text = normalize_text(value, remove_accents=True)
	text = re.sub(r"[^a-z0-9]+", "_", text)
	return text.strip("_")

def merge_points(points: list[dict], key_normalizer=None) -> list[dict]:
	if key_normalizer is None:
		key_normalizer = normalize_token
	
	merged: dict[str, dict] = {}

	for point in points:
		key = (
			f"{round(float(point['lat']), 6)}|{round(float(point['lng']), 6)}|"
			f"{key_normalizer(point.get('nome', ''))}"
		)

		if key not in merged:
			merged[key] = {
				**point,
				"categorias": sorted(set(point.get("categorias") or [])),
				"fontes": sorted(set(point.get("fontes") or [])),
			}
			continue

		existing = merged[key]
		
		categorias = set(existing.get("categorias") or [])
		categorias.update(point.get("categorias") or [])
		existing["categorias"] = sorted(categorias)

		fontes = set(existing.get("fontes") or [])
		fontes.update(point.get("fontes") or [])
		existing["fontes"] = sorted(fontes)

	return list(merged.values())


def extract_float_coordinate(value) -> float | None:
	try:
		return float(value)
	except (TypeError, ValueError):
		return None
