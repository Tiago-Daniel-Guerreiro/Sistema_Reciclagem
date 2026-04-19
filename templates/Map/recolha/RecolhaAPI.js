const RecolhaAPI = (function () {
    const API_BASE = `${window.location.origin}/api`;
    const CACHE_VERSION = 'recolha_v5';
    const CACHE_VERSION_KEY = 'recolha_cache_version';

    let _pontos = null;
    let _categoriasGerais = null;
    let _categoriasEletronicos = null;

    function _ensureCacheVersion() {
        const current = localStorage.getItem(CACHE_VERSION_KEY);
        if (current === CACHE_VERSION) return;

        localStorage.removeItem('recolha_categorias_gerais');
        localStorage.removeItem('recolha_categorias_eletronicos');
        localStorage.removeItem('recolha_pontos');
        localStorage.setItem(CACHE_VERSION_KEY, CACHE_VERSION);

        _categoriasGerais = null;
        _categoriasEletronicos = null;
        _pontos = null;
    }

    async function _fetchCategorias() {
        const res = await fetch(`${API_BASE}/categorias`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        // API retorna array direto ou objeto com data/categories
        const cats = Array.isArray(data) ? data : (data.data || data.categories || []);
        return cats;
    }

    async function _fetchAllPontos() {
        const allPontos = [];
        let offset = 0;
        const limit = 1000;
        let hasMore = true;

        while (hasMore) {
            const url = `${API_BASE}/pontos?limit=${limit}&offset=${offset}`;
            const res = await fetch(url);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            const pts = Array.isArray(data) ? data : (data.data || data.points || []);
            if (pts.length === 0) break;

            allPontos.push(...pts);

            // Verificar se há mais (via meta.has_more ou comparando com limit)
            if (data.meta?.has_more === false || pts.length < limit) hasMore = false;
            else offset += limit;
        }

        return allPontos;
    }

    async function _loadSnapshot() {
        const snapshot = localStorage.getItem('snapshot_cache');

        if (snapshot != null) {
            try {
                return JSON.parse(snapshot);
            } catch (e) {
                console.warn('[RecolhaAPI._loadSnapshot] Cache inválido, limpando:', e);
                localStorage.removeItem('snapshot_cache');
            }
        }

        try {
            const res = await fetch('./snapshot.json');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            localStorage.setItem('snapshot_cache', JSON.stringify(data));
            return data;
        } catch (e) {
            console.warn('[RecolhaAPI._loadSnapshot] Fetch falhou:', e);
        }

        return null;
    }

    async function sync() {
        _ensureCacheVersion();

        try {
            // Sempre fetch completo da API
            const allCategorias = await _fetchCategorias();
            const pontosRaw = await _fetchAllPontos();

            _categoriasGerais = allCategorias.filter(c => !c.eletronico);
            _categoriasEletronicos = allCategorias.filter(c => c.eletronico);

            // Transformar pontos da API para o formato esperado
            _pontos = pontosRaw.map(p => ({
                id: p.id,
                lat: p.lat,
                lng: p.lng,
                nome: p.nome,
                recolha: true,
                dados_recolha: {
                    categorias: p.categorias || [],
                    fontes: p.fontes || 'desconhecida'
                }
            }));

            localStorage.setItem('recolha_categorias_gerais', JSON.stringify(_categoriasGerais));
            localStorage.setItem('recolha_categorias_eletronicos', JSON.stringify(_categoriasEletronicos));
            localStorage.setItem('recolha_pontos', JSON.stringify(_pontos));
            localStorage.setItem('recolha_pontos_count', String(_pontos?.length || 0));

            return {
                categoriasGerais: _categoriasGerais,
                categoriasEletronicos: _categoriasEletronicos,
                pontos: _pontos
            };
        } catch (e) {
            console.warn('[RecolhaAPI.sync] API falhou, tentando snapshot...');

            // API falhou - tentar snapshot
            const snapshot = await _loadSnapshot();

            if (snapshot?.categories?.length || snapshot?.points?.length) {
                _categoriasGerais = (snapshot.categories || []).filter(c => !c.eletronico);
                _categoriasEletronicos = (snapshot.categories || []).filter(c => c.eletronico);

                // Transformar pontos do snapshot para o formato esperado
                const pontosRaw = snapshot.points || [];
                _pontos = pontosRaw.map(p => ({
                    id: p.id,
                    lat: p.lat,
                    lng: p.lng,
                    nome: p.nome,
                    recolha: true,
                    dados_recolha: {
                        categorias: p.categorias || [],
                        fontes: p.fontes || 'desconhecida'
                    }
                }));

                localStorage.setItem('recolha_categorias_gerais', JSON.stringify(_categoriasGerais));
                localStorage.setItem('recolha_categorias_eletronicos', JSON.stringify(_categoriasEletronicos));
                localStorage.setItem('recolha_pontos', JSON.stringify(_pontos));
                localStorage.setItem('recolha_pontos_count', String(_pontos.length));

                return {
                    categoriasGerais: _categoriasGerais,
                    categoriasEletronicos: _categoriasEletronicos,
                    pontos: _pontos,
                    fromSnapshot: true
                };
            }

            // Snapshot falhou - carregar cache antigo
            if (!_categoriasGerais) _categoriasGerais = JSON.parse(localStorage.getItem('recolha_categorias_gerais') || '[]');
            if (!_categoriasEletronicos) _categoriasEletronicos = JSON.parse(localStorage.getItem('recolha_categorias_eletronicos') || '[]');
            if (!_pontos) _pontos = JSON.parse(localStorage.getItem('recolha_pontos') || '[]');

            return {
                categoriasGerais: _categoriasGerais,
                categoriasEletronicos: _categoriasEletronicos,
                pontos: _pontos,
                fromCache: true,
                warning: 'Offline - usando cache'
            };
        }
    }

    function getCategorias() {
        if (!_categoriasGerais && !_categoriasEletronicos) return null;
        return [...(_categoriasGerais || []), ...(_categoriasEletronicos || [])];
    }

    function getCategoriasGerais() {
        return _categoriasGerais || [];
    }

    function getCategoriasEletronicos() {
        return _categoriasEletronicos || [];
    }

    function getPontos() {
        if (_pontos) return _pontos;

        const rawData = localStorage.getItem('recolha_pontos');
        if (!rawData) return null;

        try {
            _pontos = JSON.parse(rawData);
            return _pontos;
        } catch (err) {
            console.error(`getPontos(): Error parsing cached data:`, err);
            localStorage.removeItem('recolha_pontos');
            localStorage.removeItem('recolha_pontos_count');
            return null;
        }
    }

    function getPontosInChunks(chunkSize = 1000) {
        const pontos = getPontos();
        if (!pontos) return [];

        const chunks = [];
        for (let i = 0; i < pontos.length; i += chunkSize) {
            chunks.push(pontos.slice(i, i + chunkSize));
        }
        return chunks;
    }

    return {
        sync,
        getCategorias,
        getCategoriasGerais,
        getCategoriasEletronicos,
        getPontos,
        getPontosInChunks
    };
})();
