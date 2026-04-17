const MapModule = (function () {
    let map = null;
    let geoJsonLayerGroup = null;
    let markersLayerGroup = null;
    let currentLocation = null;
    let _loadingTimeout = null;
    const portugalBounds = [[30.03, -31.27], [42.15, -6.19]];
    const portugalContinentalBounds = [[36.960, -9.500], [42.154, -6.189]];


    function init() {
        map = L.map('map', { zoomControl: true });

        ConfigMapDefault()

        Constants.layers['Mapa Simples'].addTo(map);
        geoJsonLayerGroup = L.layerGroup().addTo(map);
        markersLayerGroup = L.layerGroup().addTo(map);

        L.control.layers(Constants.layers).addTo(map);
    }

    function ConfigMapDefault() {
        if (!map) return;

        map.fitBounds(portugalContinentalBounds);
        map.setMaxBounds(null);
        map.setMinZoom(5);
        map.setMaxZoom(17);
    }

    function ShowAreaFitBounds(bounds, padding = [20, 20], Paint) {
        if (!map) return

        map.fitBounds(bounds, { padding });

        if (!Paint) return

        L.rectangle(bounds, {
            color: "#ff7800",
            weight: 1,
            fillColor: "#ff7800",
            fillOpacity: 0.5
        }).addTo(map);
    }

    function setLoading(isLoading) {
        if (!map) return;

        if (_loadingTimeout) clearTimeout(_loadingTimeout);

        const mapElement = map.getContainer();

        if (isLoading) {
            mapElement.setAttribute('data-loading', 'true');

            // Permitir fechar clicando no painel de fundo
            mapElement.addEventListener('click', _handleLoadingClick, { once: true });

            // Auto-hide após 15 segundos
            _loadingTimeout = setTimeout(() => {
                mapElement.setAttribute('data-loading', 'false');
                mapElement.removeEventListener('click', _handleLoadingClick);
            }, 15000);
        } else {
            mapElement.setAttribute('data-loading', 'false');
            mapElement.removeEventListener('click', _handleLoadingClick);
        }
    }

    function _handleLoadingClick(e) {
        // Fechar se clicar no fundo escuro
        if (e.target === map.getContainer()) {
            map.getContainer().setAttribute('data-loading', 'false');
            if (_loadingTimeout) clearTimeout(_loadingTimeout);
        }
    }

    function getLoading() {
        if (!map) return false;
        return map.getContainer().getAttribute('data-loading') === 'true';
    }

    function getMap() { return map; }
    function getMarkersLayerGroup() { return markersLayerGroup; }
    function getGeoJsonLayerGroup() { return geoJsonLayerGroup; }
    function getAreaStyle() { return Constants.AREA_STYLE; }
    function getCurrentLocation() { return currentLocation; }
    function setCurrentLocation(lat, lng) { currentLocation = { lat, lng }; }
    function getPortugalBoundsLeaflet() { return L.latLngBounds(portugalBounds); }
    function getPortugalContinentalBounds() { return portugalContinentalBounds; }

    function showArea(resultado) {
        if (!geoJsonLayerGroup) {
            console.warn('showArea: geoJsonLayerGroup ainda não foi inicializado');
            return;
        }

        geoJsonLayerGroup.clearLayers();

        const geojson = Format.firstValid([resultado.geojson, resultado.polygon_geojson, resultado.geometry]);

        if (!geojson) {
            console.warn('Nenhum GeoJSON encontrado para:', resultado.name);
            map.setView([parseFloat(resultado.lat), parseFloat(resultado.lon || resultado.lng)], 14);
            return;
        }

        try {
            const geoJsonLayer = L.geoJSON(geojson, {
                style: Constants.AREA_STYLE,
                className: 'area-geojson'
            }).addTo(geoJsonLayerGroup);

            map.fitBounds(geoJsonLayer.getBounds(), { padding: [50, 50], maxZoom: 16 });
        } catch (e) { console.error('Erro ao renderizar GeoJSON:', e); }
    }

    return {
        init,
        getMap,
        getMarkersLayerGroup,
        getGeoJsonLayerGroup,
        getAreaStyle,
        showArea,
        ConfigMapDefault,
        getCurrentLocation,
        setCurrentLocation,
        getPortugalBoundsLeaflet,
        getPortugalContinentalBounds,
        setLoading,
        getLoading
    };
})();
