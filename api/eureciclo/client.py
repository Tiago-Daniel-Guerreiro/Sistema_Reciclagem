from __future__ import annotations

import requests
from pathlib import Path
from html.parser import HTMLParser

from ..base_client import BaseClient

EURECICLO_CATEGORY_MAP = {
	"40": ["pilhas"],
	"41": ["pequenos_equipamentos"],
	"42": ["lampadas"],
	"43": ["grandes_equipamentos"],
}

DEFAULT_TIMEOUT = 30
EURECICLO_URL = "https://eureciclo.pt/wp-admin/admin-ajax.php?action=asl_load_stores&nonce=50a9158f74&load_all=0&layout=1&lat=38.721562857427074&lng=-9.139336599999991&nw%5B%5D=39.03548967767917&nw%5B%5D=-9.584282889062491&se%5B%5D=38.40763603717498&se%5B%5D=-8.694390310937491"


class HTMLCategoryExtractor(HTMLParser):
	def __init__(self):
		super().__init__()
		self.categories = []
		self.in_h4 = False
	
	def handle_starttag(self, tag, attrs):
		if tag == "h4":
			self.in_h4 = True
	
	def handle_endtag(self, tag):
		if tag == "h4":
			self.in_h4 = False
	
	def handle_data(self, data):
		if self.in_h4 and data:
			text = data.strip().lower()
			text = text.replace("á", "a").replace("â", "a").replace("ã", "a")
			text = text.replace("é", "e").replace("ê", "e")
			text = text.replace("í", "i")
			text = text.replace("ó", "o").replace("ô", "o")
			text = text.replace("ú", "u")
			
			if "pilha" in text:
				self.categories.append("pilhas")
			elif "pequeno" in text and "equip" in text:
				self.categories.append("pequenos_equipamentos")
			elif "lampada" in text or "lâmpada" in text:
				self.categories.append("lampadas")
			elif "grande" in text and "equip" in text:
				self.categories.append("grandes_equipamentos")


def extract_categories_from_html(html_description: str) -> list[str]:
	if not html_description:
		return []
	
	try:
		parser = HTMLCategoryExtractor()
		parser.feed(html_description)
		return sorted(set(parser.categories))
	except Exception:
		return []


class EurecicloClient(BaseClient):	
	SOURCE_NAME = "eureciclo"
	
	def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT, data_dir: str | None = None):
		if data_dir is None:
			data_dir = str(Path(__file__).parent / "data")
		
		super().__init__(data_dir=data_dir)
		self.timeout_seconds = timeout_seconds
	
	def fetch_raw_data(self) -> dict:
		try:
			response = requests.get(EURECICLO_URL, timeout=self.timeout_seconds)
			response.raise_for_status()
			stores = response.json()
		except Exception as exc:
			print(f"[eureciclo] Erro em requisição: {exc}")
			stores = []
		
		return {
			"stores": stores,
			"metadata": {
				"total_stores": len(stores),
			}
		}
	
	def normalize_data(self, raw_data: dict) -> list[dict]:
		normalized_points = []
		
		for store in raw_data.get("stores", []):
			point = self._extract_point(store)
			if point:
				normalized_points.append(point)
		
		return normalized_points
	
	def _extract_point(self, store: dict) -> dict | None:
		try:
			lat = float(store.get("lat", 0))
			lng = float(store.get("lng", 0))
		except (TypeError, ValueError):
			return None
		
		if lat == 0 or lng == 0:
			return None
		
		nome = store.get("title") or store.get("city") or "Ponto de Recolha"
		
		description = store.get("description", "")
		categories = extract_categories_from_html(description)
		
		if not categories:
			category_id = store.get("categories")
			if category_id and str(category_id) in EURECICLO_CATEGORY_MAP:
				categories = EURECICLO_CATEGORY_MAP[str(category_id)]
		
		if not categories:
			return None
		
		return {
			"nome": str(nome).strip(),
			"categorias": sorted(categories),
			"lat": lat,
			"lng": lng,
			"fontes": ["eureciclo"],
		}

