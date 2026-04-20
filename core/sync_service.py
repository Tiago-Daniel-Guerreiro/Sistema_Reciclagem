from __future__ import annotations
import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from api.overpass.client import OverpassClient
from api.dadosabertos.client import DadosAbertosClient
from api.eureciclo.client import EurecicloClient

CLIENTS = {
	"overpass": OverpassClient(),
	"dadosabertos": DadosAbertosClient(),
	"eureciclo": EurecicloClient(),
}

class WeeklySyncService:
	def __init__(self, db_manager, interval_days: int = 7, check_interval_seconds: int = 3600):
		self.db = db_manager
		self.interval_days = interval_days
		self.check_interval_seconds = check_interval_seconds
		self.clients = CLIENTS
		self._thread = None
		self._stop_event = threading.Event()

	def _parse_iso(self, value: str | None) -> datetime | None:
		if not value:
			return None
		try:
			return datetime.fromisoformat(value.replace("Z", "+00:00"))
		except Exception:
			return None

	def should_sync(self, source: str) -> bool:
		state = self.db.get_sync_state(source)
		if not state or not state.get("last_sync_at"):
			return True

		last_sync = self._parse_iso(state.get("last_sync_at"))
		if not last_sync:
			return True

		return datetime.now(timezone.utc) - last_sync >= timedelta(days=self.interval_days)

	def _run_source_sync(self, source: str) -> dict:
		client = self.clients[source]
		print(f"[Sync] source={source} start", flush=True)

		try:
			sync_success = client.sync()
			normalized_points = client.load_filtered_data()
			created = self.db.insert_points(normalized_points)
			self.db.set_sync_state(source, "success", None)
			
			print(
				f"[Sync] source={source} ok loaded={len(normalized_points)} created={created}",
				flush=True,
			)
			return {
				"success": True,
				"source": source,
				"loaded_points": len(normalized_points),
				"created": created,
				"from_cache": False,
			}
		except Exception as exc:
			err_text = str(exc).strip() or f"{exc.__class__.__name__}"
			
			try:
				cached_points = client.load_filtered_data()
				if cached_points:
					created = self.db.insert_points(cached_points)
					self.db.set_sync_state(source, "cached", err_text)
					print(
						f"[Sync] source={source} fallback_cache=True created={created} error={err_text}",
						flush=True,
					)
					return {
						"success": True,
						"source": source,
						"loaded_points": len(cached_points),
						"created": created,
						"from_cache": True,
						"warning": f"sync falhou, usado cache: {err_text}",
					}
			except Exception:
				pass
			
			print(f"[Sync] source={source} failed error={err_text}", flush=True)
			raise RuntimeError(err_text) from exc

	def _export_daily_snapshot(self) -> dict:
		try:
			snapshot_dir = Path(__file__).parent.parent / "templates" / "Map" / "data"
			snapshot_dir.mkdir(parents=True, exist_ok=True)
			snapshot_path = snapshot_dir / "snapshot.json"
			
			new_snapshot = self.db.export_snapshot()
			
			if snapshot_path.exists():
				try:
					with open(snapshot_path, "r", encoding="utf-8") as f:
						old_snapshot = json.load(f)

					if old_snapshot.get("categories") == new_snapshot.get("categories") and \
					   old_snapshot.get("points") == new_snapshot.get("points"):
						print("[Snapshot] no changes - skipped", flush=True)
						return {"skipped": True}
				except Exception:
					pass
			

			with open(snapshot_path, "w", encoding="utf-8") as f:
				json.dump(new_snapshot, f, ensure_ascii=False, indent=2)
			
			print(f"[Snapshot] saved cat={len(new_snapshot['categories'])} pts={len(new_snapshot['points'])}", flush=True)
			return {
				"saved": True,
				"categories": len(new_snapshot["categories"]),
				"points": len(new_snapshot["points"]),
			}
		except Exception as e:
			print(f"[Snapshot] export falhou: {e}", flush=True)
			return {"error": str(e)}

	def _should_refresh_snapshot(self) -> bool:
		try:
			snapshot_path = Path(__file__).parent.parent / "templates" / "Map" / "data" / "snapshot.json"
			if not snapshot_path.exists():
				return True
			
			from datetime import datetime, timedelta, timezone
			file_time = datetime.fromtimestamp(snapshot_path.stat().st_mtime, tz=timezone.utc)
			age = datetime.now(timezone.utc) - file_time
			return age > timedelta(days=1)
		except Exception:
			return False

	def run_sync(self, force: bool = False) -> dict:
		due_sources = [source for source in self.clients if force or self.should_sync(source)]
		snapshot_result = None
		
		if not due_sources and not force and self._should_refresh_snapshot():
			print("[Sync] Atualizando snapshot (1 dia passado)...", flush=True)
			snapshot_result = self._export_daily_snapshot()
			return {
				"success": True,
				"skipped": True,
				"reason": "snapshot_refresh",
				"snapshot": snapshot_result,
			}
		
		if not due_sources:
			print("[Sync] skipped (not_due)", flush=True)
			return {
				"success": True,
				"skipped": True,
				"reason": "not_due",
				"next_sync_days": self.interval_days,
				"sources": list(self.clients.keys()),
			}

		results = []
		errors = []

		# Sincronizar em paralelo usando ThreadPoolExecutor
		print(f"[Sync] Iniciando {len(due_sources)} sincronizações em paralelo: {due_sources}", flush=True)
		print(f"[Sync] Iniciando {len(due_sources)} sincronizações em paralelo: {due_sources}", flush=True)
		with ThreadPoolExecutor(max_workers=len(due_sources)) as executor:
			# Submeter todas as sincronizações
			future_to_source = {
				executor.submit(self._run_source_sync, source): source 
				for source in due_sources
			}
			
			# Aguardar que todas as sincronizações acabem
			for future in as_completed(future_to_source):
				source = future_to_source[future]
				try:
					result = future.result()
					results.append(result)
				except Exception as exc:
					err_text = str(exc).strip() or f"{exc.__class__.__name__}"
					self.db.set_sync_state(source, "error", err_text)
					errors.append({"source": source, "error": err_text})
					print(f"[Sync] source={source} failed in parallel: {err_text}", flush=True)

		if not errors:
			with self.db.connection() as conn:
				pass
			
			snapshot_result = self._export_daily_snapshot()

		print(
			f"[Sync] finished success={len(errors) == 0} due={due_sources} errors={len(errors)}",
			flush=True,
		)

		return {
			"success": len(errors) == 0,
			"skipped": False,
			"due_sources": due_sources,
			"results": results,
			"snapshot": snapshot_result if not errors else None,
			"errors": errors,
		}

	def _loop(self):
		while not self._stop_event.is_set():
			self.run_sync(force=False)
			self._stop_event.wait(self.check_interval_seconds)

	def start(self):
		if self._thread and self._thread.is_alive():
			return

		self._stop_event.clear()
		self._thread = threading.Thread(target=self._loop, name="weekly-sync-thread", daemon=True)
		self._thread.start()

	def stop(self):
		self._stop_event.set()
		if self._thread and self._thread.is_alive():
			self._thread.join(timeout=5)
