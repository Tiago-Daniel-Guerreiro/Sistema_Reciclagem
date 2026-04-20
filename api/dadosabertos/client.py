from __future__ import annotations

import requests
from pathlib import Path

from ..base_client import BaseClient

DADOSABERTOS_SOURCES = [
	{
		"name": "ecoilhas_subterraneos",
		"categories": ["ecoilhas"],
		"url": "https://services.arcgis.com/1dSrzEWVQn5kHHyK/arcgis/rest/services/Amb_EcopontosSubterraneos/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson",
	},
	{
		"name": "papel",
		"categories": ["papel"],
		"url": "https://services.arcgis.com/1dSrzEWVQn5kHHyK/arcgis/rest/services/Amb_Reciclagem/FeatureServer/1/query?outFields=*&where=1%3D1&f=geojson",
	},
	{
		"name": "oleos_alimentares",
		"categories": ["oleos_alimentares"],
		"url": "https://services.arcgis.com/1dSrzEWVQn5kHHyK/arcgis/rest/services/Amb_Reciclagem/FeatureServer/4/query?outFields=*&where=1%3D1&f=geojson",
	},
	{
		"name": "vidros",
		"categories": ["vidro"],
		"url": "https://services.arcgis.com/1dSrzEWVQn5kHHyK/arcgis/rest/services/Amb_Reciclagem/FeatureServer/6/query?outFields=*&where=1%3D1&f=geojson",
	},
	{
		"name": "ecopontos_misto",
		"categories": ["vidro", "papel", "plastico"],
		"url": "https://services.arcgis.com/1dSrzEWVQn5kHHyK/arcgis/rest/services/Amb_Reciclagem/FeatureServer/2/query?outFields=*&where=1%3D1&f=geojson",
	},
	{
		"name": "equipamentos_eletricos",
		"categories": ["equipamentos_eletricos_e_electronicos"],
		"url": "https://services.arcgis.com/1dSrzEWVQn5kHHyK/arcgis/rest/services/Amb_Reciclagem/FeatureServer/5/query?outFields=*&where=1%3D1&f=geojson",
	},
	{
		"name": "ecoilhas_completo",
		"categories": ["lixo_geral", "vidro", "papel", "plastico"],
		"url": "https://services.arcgis.com/1dSrzEWVQn5kHHyK/arcgis/rest/services/Amb_Reciclagem/FeatureServer/5/query?outFields=*&where=1%3D1&f=geojson",
	},
]

DEFAULT_TIMEOUT = 30


class DadosAbertosClient(BaseClient):	
	SOURCE_NAME = "dadosabertos"
	DEFAULT_URLS = [source["url"] for source in DADOSABERTOS_SOURCES]
	
	def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT, data_dir: str | None = None):
		if data_dir is None:
			data_dir = Path(__file__).parent / "data"
		
		super().__init__(data_dir=str(data_dir))
		self.timeout_seconds = timeout_seconds
	
	def _request_geojson(self, url: str) -> dict:
		response = requests.get(url, timeout=self.timeout_seconds)
		response.raise_for_status()
		return response.json()
	
	def fetch_raw_data(self) -> dict:
		all_sources = []
		total_features = 0
		
		for source_config in DADOSABERTOS_SOURCES:
			source_name = source_config["name"]
			categories = source_config["categories"]
			url = source_config["url"]
			
			try:
				print(f"[dadosabertos] Requisitando {source_name}...")
				geojson = self._request_geojson(url)
				features = geojson.get("features", [])
				
				all_sources.append({
					"source": source_name,
					"categories": categories,
					"features": features,
					"count": len(features),
				})
				
				total_features += len(features)
				print(f"[dadosabertos] {source_name}: {len(features)} features")
				
			except Exception as exc:
				print(f"[dadosabertos] Erro em {source_name}: {exc}")
		return {
			"features_by_source": all_sources,
			"metadata": {
				"total_features": total_features,
				"sources_count": len(all_sources),
			}
		}
	
	def normalize_data(self, raw_data: dict) -> list[dict]:
		normalized_points = []
		
		for source_item in raw_data.get("features_by_source", []):
			source_name = source_item["source"]
			categories = source_item["categories"]
			features = source_item["features"]
			
			for feature in features:
				point = self._extract_point(feature, categories)
				if point:
					normalized_points.append(point)
		
		return normalized_points
	
	def _extract_point(self, feature: dict, categories: list[str]) -> dict | None:
		geometry = feature.get("geometry") or {}
		coordinates = geometry.get("coordinates") or []
		
		if not isinstance(coordinates, list) or len(coordinates) < 2:
			return None
		
		try:
			lng = float(coordinates[0])
			lat = float(coordinates[1])
		except (TypeError, ValueError):
			return None
		
		properties = feature.get("properties") or {}
		nome = (
			properties.get("PRSL_LOCAL")
			or properties.get("TPRS_DESC")
			or properties.get("TOP_MOD_1")
			or "Ponto de Recolha"
		)
		
		return {
			"nome": str(nome).strip(),
			"categorias": sorted(categories),
			"lat": lat,
			"lng": lng,
			"fontes": ["dadosabertos"],
		}