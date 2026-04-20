from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from .base_sync import atomic_write_json, now_iso
from core.point_filters import normalize_and_validate_point

class BaseClient(ABC):
	SOURCE_NAME: str  # p.ex. "overpass", "ecoponto", "dadosabertos"
	DEFAULT_URLS: list[str]  # Lista de URLs com fallback
	
	def __init__(self, data_dir: str | None = None):
		if data_dir is None:
			self.source_dir = Path(__file__).parent / "data" / self.SOURCE_NAME
		else:
			self.source_dir = Path(data_dir)
		
		self.temp_dir = self.source_dir / "temp"
		
		self.temp_dir.mkdir(parents=True, exist_ok=True)
		self.source_dir.mkdir(parents=True, exist_ok=True)
	
	@property
	def raw_temp_path(self) -> Path:
		return self.temp_dir / f"{self.SOURCE_NAME}_raw.json"
	
	@property
	def filtered_path(self) -> Path:
		return self.source_dir / f"{self.SOURCE_NAME}_filtered.json"
	
	@abstractmethod
	def fetch_raw_data(self) -> dict | list:
		pass
	
	@abstractmethod
	def normalize_data(self, raw_data: dict | list) -> list[dict]:
		pass
	
	def save_raw_data(self, data: dict | list) -> None:
		atomic_write_json(str(self.raw_temp_path), {
			"timestamp": now_iso(),
			"source": self.SOURCE_NAME,
			"data": data,
		})
	
	def sync(self) -> bool:
		try:
			raw_data = self.fetch_raw_data()
			self.save_raw_data(raw_data)
			normalized = self.normalize_data(raw_data)
			
			validated_points = []
			for point in normalized:
				validated = normalize_and_validate_point(point)
				if validated and isinstance(validated, dict):
					validated_points.append(validated)
			
			atomic_write_json(str(self.filtered_path), validated_points)
			
			print(f"[{self.SOURCE_NAME}] sync: {len(normalized)} | raw {len(validated_points)} validated")
		
			return True
			
		except Exception as exc:
			print(f"[{self.SOURCE_NAME}] Sincronização falhou: {exc}")
			print(f"[{self.SOURCE_NAME}] Usando ficheiro anterior de {self.filtered_path}")
			
			if not self.filtered_path.exists():
				raise RuntimeError(
					f"Sincronização de {self.SOURCE_NAME} falhou e ficheiro anterior não existe"
				) from exc
			
			return False
	
	def load_filtered_data(self) -> list[dict]:
		if not self.filtered_path.exists():
			return []
		
		try:
			with open(self.filtered_path, 'r', encoding='utf-8') as f:
				return json.load(f)
		except (json.JSONDecodeError, IOError) as exc:
			print(f"[{self.SOURCE_NAME}] Erro ao carregar {self.filtered_path}: {exc}")
			return []
