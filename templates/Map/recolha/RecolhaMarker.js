const RecolhaMarker = (function () {
    let _clusterGroup = null;
    let _markers = {};
    let _visibleIds = new Set();
    let _abortController = null;
    let _categoryIndex = null;
    let _categoryIndexSource = null;
    let _lastTiposSignature = '';
    let _lastPontosSource = null;
    const BATCH_SIZE = 100;
    const BATCH_DELAY_MS = 2;

    function _buildTiposSignature(tiposSet) {
        return Array.from(tiposSet).sort().join('|');
    }

    function _ensureCategoryIndex(pontos) {
        if (_categoryIndex && _categoryIndexSource === pontos) return;

        _categoryIndex = new Map();
        _categoryIndexSource = pontos;

        for (let i = 0; i < pontos.length; i++) {
            const ponto = pontos[i];
            if (!ponto.recolha || !ponto.dados_recolha || !Array.isArray(ponto.dados_recolha.categorias)) continue;

            for (let j = 0; j < ponto.dados_recolha.categorias.length; j++) {
                const categoria = String(ponto.dados_recolha.categorias[j]);
                if (!_categoryIndex.has(categoria)) _categoryIndex.set(categoria, []);
                _categoryIndex.get(categoria).push(ponto);
            }
        }
    }

    function _filtrarPontosPorCategorias(todosPontos, tiposSet) {
        if (!todosPontos?.length || tiposSet.size === 0) return [];

        _ensureCategoryIndex(todosPontos);
        const uniqueById = new Map();

        tiposSet.forEach(tipo => {
            const strTipo = String(tipo);
            const pontosDaCategoria = _categoryIndex.get(strTipo);
            if (!pontosDaCategoria?.length) return;

            for (let i = 0; i < pontosDaCategoria.length; i++) {
                const ponto = pontosDaCategoria[i];
                if (!uniqueById.has(ponto.id)) uniqueById.set(ponto.id, ponto);
            }
        });

        return Array.from(uniqueById.values());
    }

    function _setupCluster(layer) {
        if (!layer) return;

        _clusterGroup = L.markerClusterGroup({
            maxClusterRadius: 120,
            disableClusteringAtZoom: 18,
            removeOutsideVisibleBounds: true,
            animate: false,
            animateAddingMarkers: false,
            chunkedLoading: true,
            chunkInterval: 8,
            chunkDelay: 16,
            iconCreateFunction: (c) => L.divIcon({
                html: `<div class="marker-cluster-icon">${c.getChildCount()}</div>`,
                className: 'marker-recolha cluster',
                iconSize: [40, 40],
                iconAnchor: [20, 40]
            })
        });
        layer.addLayer(_clusterGroup);
    }

    function _createMarker(ponto) {
        if (_markers[ponto.id]) return _markers[ponto.id];

        const marker = L.marker([ponto.lat, ponto.lng], {
            icon: L.divIcon({
                className: 'marker-recolha',
                html: '<div class="marker-recolha-icon"><img src="icons/reciclagem.svg"></div>',
                iconSize: [32, 32],
                iconAnchor: [16, 32],
                popupAnchor: [0, -32]
            })
        });
        marker.on('click', () => DetalhesModule.abrir(ponto));
        return (_markers[ponto.id] = marker);
    }

    function focus(ponto, zoom = 16) {
        if (!ponto || !_clusterGroup) return false;
        const marker = _createMarker(ponto);
        try {
            // Garante que o marker é mostrado mesmo dentro de clusters
            _clusterGroup.zoomToShowLayer(marker, () => {
                MapModule.getMap()?.setView([ponto.lat, ponto.lng], zoom);
                // Abre detalhes em vez de depender de popup (mais consistente)
                if (DetalhesModule?.abrir) DetalhesModule.abrir(ponto);
            });
            return true;
        } catch (e) {
            console.warn('[RecolhaMarker.focus] Falha ao focar ponto:', e);
            return false;
        }
    }

    async function _renderBatch(pontos, signal) {
        if (!pontos?.length || !_clusterGroup) return;

        let index = 0;
        let batchNum = 0;

        while (index < pontos.length && !signal?.aborted) {
            batchNum++;
            const endIndex = Math.min(index + BATCH_SIZE, pontos.length);
            const toAdd = [];

            for (let i = index; i < endIndex; i++) {
                const ponto = pontos[i];
                if (!_visibleIds.has(ponto.id)) {
                    toAdd.push(_createMarker(ponto));
                    _visibleIds.add(ponto.id);
                }
            }

            if (toAdd.length > 0 && _clusterGroup) {
                _clusterGroup.addLayers(toAdd);
            }

            index = endIndex;

            // Pequeno delay entre batches para permitir UI responder
            if (index < pontos.length && !signal?.aborted) {
                await new Promise(r => setTimeout(r, BATCH_DELAY_MS));
            }
        }
    }

    async function renderMarkersEmChunks(pontos, signal) {
        if (!pontos?.length) return;
        await _renderBatch(pontos, signal);
    }

    async function removeMarkersEmChunks(ids, signal) {
        if (!ids?.length || !_clusterGroup) return;

        let index = 0;

        while (index < ids.length && !signal?.aborted) {
            const endIndex = Math.min(index + BATCH_SIZE, ids.length);
            const toRemove = [];

            for (let i = index; i < endIndex; i++) {
                const id = ids[i];
                if (_markers[id]) {
                    toRemove.push(_markers[id]);
                    _visibleIds.delete(id);
                }
            }

            if (toRemove.length > 0 && _clusterGroup) {
                _clusterGroup.removeLayers(toRemove);
            }

            index = endIndex;

            if (index < ids.length && !signal?.aborted) {
                await new Promise(r => setTimeout(r, BATCH_DELAY_MS));
            }
        }
    }

    async function aplicarFiltros(todosPontos, tiposSet) {
        // Se cluster foi limpado mas agora tem filtros, reconstruir
        if (!_clusterGroup && tiposSet.size > 0) {
            const markersLayer = MapModule.getMarkersLayerGroup?.();
            if (markersLayer) init(markersLayer);
        }

        if (!_clusterGroup) return;

        const tiposSignature = _buildTiposSignature(tiposSet);
        if (_lastTiposSignature === tiposSignature && _lastPontosSource === todosPontos) return;

        _lastTiposSignature = tiposSignature;
        _lastPontosSource = todosPontos;

        if (_abortController) _abortController.abort();
        _abortController = new AbortController();
        const signal = _abortController.signal;

        if (tiposSet.size === 0) {
            limpar();
            return;
        }

        const filtrados = _filtrarPontosPorCategorias(todosPontos, tiposSet);
        const filtradosSet = new Set(filtrados.map(p => p.id));

        const toRemove = Array.from(_visibleIds).filter(id => !filtradosSet.has(id));
        if (toRemove.length) await removeMarkersEmChunks(toRemove, signal);

        const toAdd = filtrados.filter(p => !_visibleIds.has(p.id));
        if (toAdd.length) await renderMarkersEmChunks(toAdd, signal);
    }

    function limpar() {
        if (_abortController) _abortController.abort();
        if (_clusterGroup) {
            _clusterGroup.clearLayers();
            // Remove cluster da camada e limpa referência para forçar recriação
            const map = MapModule.getMap?.();
            if (map && _clusterGroup) map.removeLayer(_clusterGroup);
            _clusterGroup = null;
        }
        _markers = {};
        _visibleIds.clear();
        _lastTiposSignature = '';
        _lastPontosSource = null;
    }

    function init(markersLayer) {
        if (_clusterGroup) return;
        _setupCluster(markersLayer);
    }

    return {
        init,
        renderMarkersEmChunks,
        aplicarFiltros,
        limpar,
        getClusterGroup: () => _clusterGroup,
        focus
    };
})();