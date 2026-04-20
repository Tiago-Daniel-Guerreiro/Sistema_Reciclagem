from __future__ import annotations

import requests
import time
from pathlib import Path

from ..base_client import BaseClient
from .filters import filter_and_format_elements
from core.config import PORTUGAL_BBOX

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_FALLBACK_URLS = [
	"https://overpass-api.de/api/interpreter",
	"https://overpass.kumi.systems/api/interpreter",
]
DEFAULT_TIMEOUT = 120

def build_overpass_query(bbox: tuple[float, float, float, float], timeout_seconds: int) -> str:
	south, west, north, east = bbox
	return f"""[out:json][timeout:{timeout_seconds}];
(
	node["amenity"="recycling"]({south},{west},{north},{east});
	way["amenity"="recycling"]({south},{west},{north},{east});

	node["organic"]({south},{west},{north},{east});
	way["organic"]({south},{west},{north},{east});

	node["recycling"]({south},{west},{north},{east});
	way["recycling"]({south},{west},{north},{east});

	node["waste"]({south},{west},{north},{east});
	way["waste"]({south},{west},{north},{east});

	node["electronics_repair"]({south},{west},{north},{east});
	way["electronics_repair"]({south},{west},{north},{east});
);
out center tags;"""


class OverpassClient(BaseClient):
	SOURCE_NAME = "overpass"
	DEFAULT_URLS = OVERPASS_FALLBACK_URLS

	def __init__(self, base_url: str = DEFAULT_OVERPASS_URL, timeout_seconds: int = DEFAULT_TIMEOUT, data_dir: str | None = None):
		if data_dir is None:
			data_dir = str(Path(__file__).parent / "data")
		
		super().__init__(data_dir=str(data_dir))
		self.base_url = base_url
		self.timeout_seconds = timeout_seconds

	def _request_elements(self, bbox: tuple[float, float, float, float], base_url: str, retry_count: int = 3, backoff_base: int = 2) -> list[dict]:
		query = build_overpass_query(bbox=bbox, timeout_seconds=self.timeout_seconds)
		
		for attempt in range(retry_count):
			try:
				response = requests.post(
					base_url,
					data={"data": query},
					headers={"Content-Type": "application/x-www-form-urlencoded"},
					timeout=self.timeout_seconds + 30,
				)
				response.raise_for_status()
				body = response.json()
				return body.get("elements", [])
			except (requests.Timeout, requests.ConnectionError) as e:
				if attempt < retry_count - 1:
					wait_time = backoff_base ** attempt
					print(f"[Overpass] Timeout (tentativa {attempt+1}/{retry_count}), aguardando {wait_time}s...", flush=True)
					time.sleep(wait_time)
					continue
				else:
					raise
			except requests.HTTPError as e:
				if 500 <= e.response.status_code < 600 and attempt < retry_count - 1:
					wait_time = backoff_base ** attempt
					print(f"[Overpass] HTTP {e.response.status_code} (tentativa {attempt+1}/{retry_count}), aguardando {wait_time}s...", flush=True)
					time.sleep(wait_time)
					continue
				else:
					raise

	def fetch_elements(self, bbox: tuple[float, float, float, float] = PORTUGAL_BBOX) -> list[dict]:
		urls = [self.base_url] + OVERPASS_FALLBACK_URLS
		last_error = None

		for idx, url in enumerate(urls):
			try:
				endpoint_name = url.split('/')[2]
				print(f"[Overpass] Tentando {endpoint_name}...", flush=True)
				result = self._request_elements(bbox=bbox, base_url=url, retry_count=3, backoff_base=3)
				print(f"[Overpass] Sucesso", flush=True)
				return result
			except Exception as exc:
				last_error = exc
				endpoint_name = url.split('/')[2]
				print(f"[Overpass] Erro em {endpoint_name}", flush=True)
				if idx < len(urls) - 1:
					time.sleep(2)

		if last_error:
			raise last_error
		return []



	def fetch_raw_data(self) -> dict | list:
		elements = self.fetch_elements()
		return {
			"elements": elements,
			"metadata": {
				"total_elements": len(elements),
			}
		}

	def normalize_data(self, raw_data: dict | list) -> list[dict]:
		elements = raw_data.get("elements", []) if isinstance(raw_data, dict) else []
		return filter_and_format_elements(elements)