from __future__ import annotations

GENERIC_RECYCLING_CATEGORY = "unspecified_recycling"
DEFAULT_POINT_NAME = "Ponto de recolha"
NO_VALUES = {"no", "false", "0", "none", "null", ""}
ORGANIC_ACCEPTED = {"yes", "only"}
YES_VALUES = {"yes", "true", "1"}

EXCLUDED_RECYCLING_SUFFIXES = {"pet", "a2a"}


def _normalize_token(value: str | None) -> str:
	if not value:
		return ""
	token = value.strip().lower()
	token = token.replace(";", "_").replace(":", "_")
	token = token.replace("-", "_").replace(" ", "_")
	while "__" in token:
		token = token.replace("__", "_")
	return token.strip("_")


def _normalized_tag_value(tags: dict, key: str) -> str:
	return _normalize_token(str(tags.get(key, "")))


def _is_not_no(value: str) -> bool:
	return value not in NO_VALUES


def _extract_recycling_subtags(tags: dict) -> tuple[set[str], list[str]]:
	categorias: set[str] = set()
	raw_subtags: list[str] = []

	for key, raw_value in tags.items():
		if not key.startswith("recycling:"):
			continue

		normalized_value = _normalize_token(str(raw_value))
		if not normalized_value or not _is_not_no(normalized_value):
			continue

		suffix = _normalize_token(key[len("recycling:") :])
		if not suffix:
			continue
		if suffix in {"*", "yes"}:
			categorias.add(GENERIC_RECYCLING_CATEGORY)
			continue
		if suffix in EXCLUDED_RECYCLING_SUFFIXES:
			continue

		raw_subtags.append(suffix)
		if _is_not_no(suffix):
			categorias.add(suffix)

	return categorias, sorted(set(raw_subtags))


def _extract_categories(tags: dict) -> tuple[list[str], list[str]]:
	categorias: set[str] = set()
	recycling_subtags_categories, recycling_subtags_raw = _extract_recycling_subtags(tags)
	categorias.update(recycling_subtags_categories)

	organic_value = _normalized_tag_value(tags, "organic")
	if organic_value in ORGANIC_ACCEPTED:
		categorias.add("organic")

	recycling_value = _normalized_tag_value(tags, "recycling")
	if recycling_value and _is_not_no(recycling_value):
		categorias.add(GENERIC_RECYCLING_CATEGORY)

	waste_value = str(tags.get("waste", "")).strip()
	if waste_value:
		for part in waste_value.split(";"):
			normalized_part = _normalize_token(part)
			if not normalized_part:
				continue
			if normalized_part in YES_VALUES:
				categorias.add(GENERIC_RECYCLING_CATEGORY)
				continue
			if normalized_part in EXCLUDED_RECYCLING_SUFFIXES:
				continue
			if _is_not_no(normalized_part):
				categorias.add(normalized_part)

	repair_value = _normalized_tag_value(tags, "electronics_repair")
	if repair_value and _is_not_no(repair_value):
		if repair_value in YES_VALUES:
			categorias.add("electronics_repair")
		else:
			categorias.add(f"electronics_repair_{repair_value}")

	return sorted(categorias), recycling_subtags_raw


def _extract_coords(element: dict) -> tuple[float, float] | None:
	lat = element.get("lat") or element.get("center", {}).get("lat")
	lng = element.get("lon") or element.get("center", {}).get("lon")
	if lat is None or lng is None:
		return None
	return float(lat), float(lng)


def format_element(element: dict) -> dict | None:
	tags = element.get("tags") or {}
	categories, recycling_subtags_raw = _extract_categories(tags)
	if not categories:
		return None

	coords = _extract_coords(element)
	if not coords:
		return None

	lat, lng = coords

	return {
		"nome": tags.get("name") or tags.get("operator") or tags.get("brand") or DEFAULT_POINT_NAME,
		"categorias": categories,
		"lat": lat,
		"lng": lng,
		"fontes": ["overpass"],
	}


def filter_and_format_elements(elements: list[dict]) -> list[dict]:
	pontos: list[dict] = []
	for element in elements:
		ponto = format_element(element)
		if ponto:
			pontos.append(ponto)
	return pontos
