const PontosMarker = (function () {
    const CLASS_MAP = {
        'recolha': Constants.MARKER_CLASSES.pontos_recolha,
        'manual': Constants.MARKER_CLASSES.manual,
        'location': Constants.MARKER_CLASSES.location,
        'search': Constants.MARKER_CLASSES.search
    };

    function getMarkerClass(ponto) {
        if (ponto.recolha) return CLASS_MAP.recolha;
        return CLASS_MAP[ponto.source] || CLASS_MAP.search;
    }

    function applyClassesAndData(ponto) {
        if (!ponto.marker || !ponto.marker._icon) return;

        const markerClass = getMarkerClass(ponto);

        ponto.marker._icon.classList.add(markerClass);
        if (ponto.marker._shadow) ponto.marker._shadow.classList.add(markerClass);

        if (ponto.recolha && ponto.dados_recolha?.categorias?.length > 0) {
            const categoriasStr = ponto.dados_recolha.categorias.join(',');
            ponto.marker._icon.dataset.categorias = categoriasStr;
            if (ponto.marker._shadow) ponto.marker._shadow.dataset.categorias = categoriasStr;
        }
    }

    function renderMarker(ponto, layerGroup) {
        if (ponto.marker) return ponto.marker;

        ponto.marker = L.marker([ponto.lat, ponto.lng]).addTo(layerGroup);
        ponto.marker.on('click', function () { PontosManager.abrirDetalhes(ponto.id); });

        applyClassesAndData(ponto);
        return ponto.marker;
    }

    return {
        renderMarker,
        applyClassesAndData
    };
})();
