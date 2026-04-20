const ModoBreno = (function () {
    const CONFIG = {
        ativo: false,
        zoomMinimo: 12,
        viewLisboa: {
            lat: 38.77403993423842,
            lng: -9.219768869310784,
            zoom: 12
        },
        bounds: {
            minLat: 38.6731469,
            maxLat: 39.3177287,
            minLng: -9.5005266,
            maxLng: -8.7818610
        },
    };

    let currentAreaBounds;
    let savedView = null;  // Guardar view anterior

    function isActive() { return CONFIG.ativo; }
    function init() { document.getElementById('modo-breno-checkbox')?.addEventListener('change', onModoBrenoChange); }
    function isPontoEmLisboa(lat, lng) { return lat >= CONFIG.bounds.minLat && lat <= CONFIG.bounds.maxLat && lng >= CONFIG.bounds.minLng && lng <= CONFIG.bounds.maxLng; }
    function isPontoEmLisboa_Ponto(ponto) { return isPontoEmLisboa(ponto.lat, ponto.lng) }
    function MapDrawLimiter() { if (isActive() && currentAreaBounds) MapModule.getMap().panInsideBounds(currentAreaBounds, { animate: false }); }
    function getSearchViewbox_Lisboa() { return `${CONFIG.bounds.minLng},${CONFIG.bounds.minLat},${CONFIG.bounds.maxLng},${CONFIG.bounds.maxLat}`; }

    function desativarModo() {
        // Limpar clusters de recolha quando sair do modo Lisboa
        if (RecolhaMarker?.limpar) RecolhaMarker.limpar();
        MapModule.ConfigMapDefault();

        // Restaurar view anterior
        const map = MapModule.getMap();
        if (savedView) map.setView(savedView.center, savedView.zoom);

        // Reinicializar cluster para próxima utilização
        const markersLayer = MapModule.getMarkersLayerGroup?.();
        if (markersLayer && RecolhaMarker?.init) RecolhaMarker.init(markersLayer);

        // Reaplica filtros para mostrar os pontos novamente com o zoom normal
        if (RecolhaFilter?.aplicarFiltros) RecolhaFilter.aplicarFiltros();
    }

    function getBoundsLeaflet() {
        return L.latLngBounds(
            [CONFIG.bounds.minLat, CONFIG.bounds.minLng],
            [CONFIG.bounds.maxLat, CONFIG.bounds.maxLng]
        );
    }

    function onModoBrenoChange(e) {
        CONFIG.ativo = e.target.checked;

        if (CONFIG.ativo) ativarModo();
        else desativarModo();
    }

    function ativarModo() {
        const map = MapModule.getMap();
        savedView = {
            center: map.getCenter(),
            zoom: map.getZoom()
        };

        currentAreaBounds = getBoundsLeaflet();
        map.setView([CONFIG.viewLisboa.lat, CONFIG.viewLisboa.lng], CONFIG.viewLisboa.zoom);

        map.setMaxBounds(currentAreaBounds);
        map.setMinZoom(CONFIG.zoomMinimo);

        map.on('drag', MapDrawLimiter);

        refiltrarResultadosBusca();

        // Recarregar os clusters para modo Lisboa
        if (RecolhaFilter?.aplicarFiltros) RecolhaFilter.aplicarFiltros();
    }

    function refiltrarResultadosBusca() {
        if (!isActive()) return;
        PontosManager.getPontosPorSource('search').forEach(ponto => { PontosManager.removePonto(ponto.id); });
    }


    return {
        init,
        isActive,
        isPontoEmLisboa,
        isPontoEmLisboa_Ponto,
        getSearchViewbox_Lisboa,
        getBoundsLeaflet,
    };
})();
