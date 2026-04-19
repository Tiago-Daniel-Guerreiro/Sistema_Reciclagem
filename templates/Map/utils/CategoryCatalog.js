const CategoryCatalog = (function () {
    const API_BASE = `${window.location.protocol}//${window.location.hostname}:5001/api`;
    const CACHE_KEY = 'category_mapping_cache';
    const CACHE_EXPIRES_MS = 24 * 60 * 60 * 1000; // 24 horas

    let _idToKey = null;
    let _keyToId = null;

    function _getCachedMapping() {
        const cached = localStorage.getItem(CACHE_KEY);
        if (!cached) return null;

        try {
            const data = JSON.parse(cached);
            if (data.expires && data.expires > Date.now()) {
                return data.mapping;
            }
            localStorage.removeItem(CACHE_KEY);
        } catch (_) { }
        return null;
    }

    function _setCachedMapping(mapping) {
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify({
                mapping,
                expires: Date.now() + CACHE_EXPIRES_MS
            }));
        } catch (_) { }
    }

    async function load() {
        if (_idToKey) return;

        // Tentar usar cache primeiro
        const cached = _getCachedMapping();
        if (cached) {
            _idToKey = cached;
            _keyToId = {};
            Object.entries(_idToKey).forEach(([id, key]) => {
                _keyToId[key] = parseInt(id, 10);
            });
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/category-mapping`, {
                signal: AbortSignal.timeout(3000)
            });

            if (!res.ok) {
                _idToKey = {};
                _keyToId = {};
                return;
            }

            const data = await res.json();
            _idToKey = typeof data === 'object' ? data : {};
            _keyToId = {};
            Object.entries(_idToKey).forEach(([id, key]) => {
                _keyToId[key] = parseInt(id, 10);
            });

            _setCachedMapping(_idToKey);
        } catch (_) {
            _idToKey = {};
            _keyToId = {};
        }
    }

    function idToKey(id) {
        if (!_idToKey) return null;
        return _idToKey[String(id)] || null;
    }

    function keyToId(key) {
        if (!_keyToId) return null;
        return _keyToId[key] || null;
    }

    function idsToKeys(ids) {
        if (!Array.isArray(ids)) return [];
        return ids
            .map(id => idToKey(id))
            .filter(key => key !== null);
    }

    function keysToIds(keys) {
        if (!Array.isArray(keys)) return [];
        return keys
            .map(key => keyToId(key))
            .filter(id => id !== null);
    }

    function getCategoryNameById(id) {
        try {
            const namesIndex = localStorage.getItem('recolha_category_names_index');
            if (namesIndex) {
                const index = JSON.parse(namesIndex);
                return index[String(id)] || null;
            }
        } catch (_) { }
        return null;
    }

    return {
        load,
        idToKey,
        keyToId,
        idsToKeys,
        keysToIds,
        getCategoryNameById
    };
})();
