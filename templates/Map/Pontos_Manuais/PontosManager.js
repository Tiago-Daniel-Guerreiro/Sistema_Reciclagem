const PontosManager = (function () {
    const pontos = new Map();
    let _manualLoaded = false;

    function createPonto(data) {
        const lat = parseFloat(data.lat);
        const lng = parseFloat(data.lng || data.lon);

        if (isNaN(lat) || isNaN(lng)) {
            console.warn('Ponto com coordenadas inválidas ignorado:', data);
            return null;
        }

        const recolha = data.recolha === true;
        const categorias = recolha && Array.isArray(data.dados_recolha?.categorias) ? data.dados_recolha.categorias : [];

        return {
            id: data.id !== undefined ? data.id : `pt_${Date.now()}_${Math.random()}`,  // Aceita IDs numéricos ou strings
            nome: data.nome || data.name || 'Sem nome',
            lat,
            lng,
            recolha,
            dados_recolha: recolha ? { categorias } : null,
            source: data.source || 'search',
            removido: false,
            marker: null
        };
    }

    function addPonto(ponto) {
        pontos.set(ponto.id, ponto);
        return ponto;
    }

    function setPontoRichData(pontoId, richData) {
        const ponto = pontos.get(pontoId);
        if (ponto) ponto._richData = richData;
    }

    function getPontoRichData(pontoId) { return pontos.get(pontoId)?._richData || null; }

    function removePonto(id) {
        const p = pontos.get(id);
        if (p?.marker) p.marker.remove();
        pontos.delete(id);
    }

    function getAllPontos() { return Array.from(pontos.values()); }

    function getPontosPorSource(source) {
        if (source === 'recolha') return RecolhaManager?.getPontos ? (RecolhaManager.getPontos() || []) : [];

        return getAllPontos().filter(p => p.source === source);
    }

    function clearSource(source) { getPontosPorSource(source).forEach(p => removePonto(p.id)); }
    function renderMarker(ponto, layerGroup) { return PontosMarker.renderMarker(ponto, layerGroup); }
    function saveManual() { PontosStorage.saveManual(getPontosPorSource('manual')); }

    function getPontoById(id) { return pontos.get(id) || getAllPontos().find(p => p.id === id); }

    function abrirDetalhes(pontoId) {
        const ponto = getPontoById(pontoId);
        if (!ponto || !DetalhesModule?.abrir) {
            console.warn('Ponto não encontrado ou DetalhesModule indisponível');
            return;
        }

        DetalhesModule.abrir(getPontoRichData(pontoId) || ponto);
    }

    function loadManual() {
        if (_manualLoaded) return;
        _manualLoaded = true;

        const manuais = PontosStorage.loadManual();
        manuais.forEach(m => { addPonto(createPonto({ ...m, source: 'manual' })); });
    }

    function init() {
        try {
            loadManual();

            const renderManuais = () => {
                const markersLayer = MapModule?.getMarkersLayerGroup?.();
                if (!markersLayer) {
                    setTimeout(renderManuais, 100);
                    return;
                }

                const pontosParaRender = getAllPontos().filter(p => !p.marker && p.source === 'manual');
                if (pontosParaRender.length > 0) pontosParaRender.forEach(p => renderMarker(p, markersLayer));
            };

            renderManuais();
        } catch (e) { console.error('[PontosManager] Erro ao inicializar:', e); }
    }

    return {
        init,
        createPonto,
        addPonto,
        setPontoRichData,
        getPontoRichData,
        removePonto,
        getAllPontos,
        getPontoById,
        getPontosPorSource,
        clearSource,
        renderMarker,
        saveManual,
        loadManual,
        abrirDetalhes
    };
})();
