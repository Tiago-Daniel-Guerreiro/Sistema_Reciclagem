const ModoBreno = (function () {
    const CONFIG = {
        ativo: false,
        zoomMinimo: 12,
        bounds: {
            minLat: 38.6731469,
            maxLat: 39.3177287,
            minLng: -9.5005266,
            maxLng: -8.7818610
        },
    };

    let currentAreaBounds;

    function isActive() { return CONFIG.ativo; }
    function init() { document.getElementById('modo-breno-checkbox')?.addEventListener('change', onModoBrenoChange); }
    function isPontoEmLisboa(lat, lng) { return lat >= CONFIG.bounds.minLat && lat <= CONFIG.bounds.maxLat && lng >= CONFIG.bounds.minLng && lng <= CONFIG.bounds.maxLng; }
    function isPontoEmLisboa_Ponto(ponto) { return isPontoEmLisboa(ponto.lat, ponto.lng) }
    function MapDrawLimiter() { if (isActive() && currentAreaBounds) MapModule.getMap().panInsideBounds(currentAreaBounds, { animate: false }); }
    function desativarModo() {
        // Limpar clusters de recolha quando sair do modo Lisboa
        if (RecolhaMarker?.limpar) RecolhaMarker.limpar();
        MapModule.ConfigMapDefault();
    }
    function getSearchViewbox_Lisboa() { return `${CONFIG.bounds.minLng},${CONFIG.bounds.minLat},${CONFIG.bounds.maxLng},${CONFIG.bounds.maxLat}`; }

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

        currentAreaBounds = getBoundsLeaflet();

        map.fitBounds(currentAreaBounds);
        map.setMaxBounds(currentAreaBounds);
        map.setMinZoom(CONFIG.zoomMinimo);
        map.on('drag', MapDrawLimiter);

        refiltrarResultadosBusca();

        // Refrescar clusters de recolha para modo Lisboa
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
