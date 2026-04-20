from core.category_catalog import normalize_category_id

PORTUGAL_REGIONS_BBOXES = [
    
    (36.8, -9.7, 42.2, -6.0), # Portugal Continental
    (37.7, -31.3, 39.7, -24.0), # Açores
    (32.6, -17.3, 32.8, -16.7), # Madeira
]

DROP_ONLY_CATEGORIES = {
    "small_bags", "capses", "caps", "cap", "pmd", "cigarettes",
    "dog_excrement", "grey_water", "cleaning_product_packaging",
}

def is_in_portugal(lat: float, lng: float) -> bool:
    for south, west, north, east in PORTUGAL_REGIONS_BBOXES:
        if south <= lat <= north and west <= lng <= east:
            return True
    return False

def normalize_and_validate_point(point: dict) -> dict | str:
    if not isinstance(point, dict):
        return ""
    
    try:
        lat_val = point.get("lat")
        lng_val = point.get("lng")
        
        if lat_val is None or lng_val is None:
            return ""
        
        lat = float(lat_val)
        lng = float(lng_val)
    except (TypeError, ValueError):
        return ""
    
    if not is_in_portugal(lat, lng):
        return ""
    
    nome = str(point.get("nome", "")).strip() or "Ponto de Recolha"
    
    fontes_raw = point.get("fontes") or point.get("fonte") or []
    if isinstance(fontes_raw, str):
        fontes = [f.strip() for f in fontes_raw.split(",") if f.strip()]
    elif isinstance(fontes_raw, list):
        fontes = [str(f).strip() for f in fontes_raw if f]
    else:
        fontes = []
    
    if not fontes:
        fontes = ["desconhecida"]
    categorias_normalized: list[str] = []
    for raw_cat in (point.get("categorias") or []):
        if not raw_cat:
            continue
        normalized_cat = normalize_category_id(str(raw_cat).strip())
        if normalized_cat not in DROP_ONLY_CATEGORIES:
            categorias_normalized.append(normalized_cat)
    
    categorias = sorted(set(categorias_normalized))
    
    if not categorias:
        return ""
    
    return {
        "lat": lat,
        "lng": lng,
        "nome": nome,
        "fontes": fontes,
        "categorias": categorias,
    }

def remove_points_without_categories_sql(conn, now: str) -> None:
    conn.execute(
        """
        UPDATE pontos
        SET is_removed = 1,
            updated_at = ?
        WHERE is_removed = 0
          AND id NOT IN (SELECT DISTINCT ponto_id FROM ponto_categorias)
        """,
        (now,),
    )

def remove_points_outside_portugal_sql(conn, now: str) -> None:
    conditions = []
    for south, west, north, east in PORTUGAL_REGIONS_BBOXES:
        conditions.append(f"(lat BETWEEN {south} AND {north} AND lng BETWEEN {west} AND {east})")
    
    where_clause = " OR ".join(conditions)
    conn.execute(
        f"""
        UPDATE pontos
        SET is_removed = 1,
            updated_at = ?
        WHERE is_removed = 0
          AND NOT ({where_clause})
        """,
        (now,),
    )