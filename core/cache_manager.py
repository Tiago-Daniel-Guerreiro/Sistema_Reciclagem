import json
from pathlib import Path
from datetime import datetime, timedelta

class CacheManager:
    CACHE_INTERVAL_DAYS = 7
    CACHE_FILENAME = "pontos_cache.json"
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / self.CACHE_FILENAME
    
    def _read_cache(self) -> dict | None:
        if not self.cache_file.exists():
            return None
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Cache] Erro ao ler cache: {e}")
            return None
    
    def _write_cache(self, data: dict) -> bool:
        try:
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[Cache] Erro ao escrever cache: {e}")
            return False
    
    def should_update_cache(self) -> bool:
        if not self.cache_file.exists():
            return True
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            timestamp_str = cache_data.get("timestamp")
            if not timestamp_str:
                return True
            
            last_update = datetime.fromisoformat(timestamp_str)
            next_update = last_update + timedelta(days=self.CACHE_INTERVAL_DAYS)
            
            return datetime.now() >= next_update
        except Exception:
            return True
    
    def save_cache(self, pontos: list, categorias: list) -> bool:
        cache_data = {
            "pontos": pontos,
            "categorias": categorias,
            "points_count": len(pontos),
            "categories_count": len(categorias)
        }
        return self._write_cache(cache_data)
    
    def get_cache(self) -> dict | None:
        return self._read_cache()
    
    def get_cache_pontos(self) -> list:
        cache = self._read_cache()
        return cache.get("data", {}).get("pontos", []) if cache else []
    
    def get_cache_categorias(self) -> list:
        cache = self._read_cache()
        return cache.get("data", {}).get("categorias", []) if cache else []
