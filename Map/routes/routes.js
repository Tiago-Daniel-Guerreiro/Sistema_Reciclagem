const RoutesModule = (function () {
    let drawToken = 0;

    function init() { initUIListeners(); }
    function getOrigin() { return RoutesData.getOrigin(); }
    function getDestination() { return RoutesData.getDestination(); }
    function setOriginFromCoords(lat, lng) { RoutesData.setOriginFromCoords(lat, lng); }
    function setDestinationFromCoords(lat, lng) { RoutesData.setDestinationFromCoords(lat, lng); }
    function setOriginFromPonto(pontoId) { RoutesData.setOriginFromPonto(pontoId); }
    function setDestinationFromPonto(pontoId) { RoutesData.setDestinationFromPonto(pontoId); }
    function swapOriginDestination() { RoutesData.swap(); }
    function setRouteLabelVisible(visible) { RoutesMapDrawer.setLabelVisible(visible); }

    async function useCurrentLocation(el, loop = true) {
        const currentLoc = MapModule.getCurrentLocation?.();

        if (currentLoc) {
            RoutesData.setOriginFromCoords(currentLoc.lat, currentLoc.lng);
            return;
        }

        if (!loop) return;

        try {
            await SidebarModule.localizarMe(el);
            await useCurrentLocation(el, false);
        } catch (error) { console.error('Falha ao obter localização:', error); }
    }

    function initUIListeners() {
        document.getElementById('route-swap-btn').addEventListener('click', swapOriginDestination);
        document.getElementById('route-use-location-btn').addEventListener('click', (ev) => useCurrentLocation(ev.target));
    }

    function updateAndDraw() {
        updateUI();
        draw();
    }

    function clear() {
        RoutesData.clear();
        RoutesMapDrawer.clearAll();
        RoutesRenderer.displayRoute(null);
        updateUI();
    }

    function updateUI() {
        updateDisplay('route-origin-display', RoutesData.getOrigin());
        updateDisplay('route-destination-display', RoutesData.getDestination());
    }

    function updateDisplay(elementId, data) {
        const display = document.getElementById(elementId);
        if (!display) return;

        if (data) {
            display.innerHTML = RoutesData.getName(data);
            display.style.background = '#c8c8c8c8';
        } else {
            display.innerHTML = 'Não definida';
            display.style.background = '#f5f5f5';
        }
    }

    function draw() {
        // Invalida qualquer cálculo pendente
        drawToken++;
        const token = drawToken;

        const origin = RoutesData.getOrigin();
        const destination = RoutesData.getDestination();

        // Sem origem ou sem destino
        if (!origin || !destination) RoutesMapDrawer.clearAll();

        if (origin) RoutesMapDrawer.drawMarker(RoutesData.getCoords(origin), 'origin', RoutesData.getName(origin));
        if (destination) RoutesMapDrawer.drawMarker(RoutesData.getCoords(destination), 'destination', RoutesData.getName(destination));

        // Sem origem ou sem destino
        if (!origin || !destination) {
            RoutesRenderer.displayRoute(null);
            return;
        }

        // Ambos definidos: calcular e desenhar rota
        const originCoords = RoutesData.getCoords(origin);
        const destCoords = RoutesData.getCoords(destination);

        if (!originCoords || !destCoords) {
            console.error('Coordenadas inválidas');
            return;
        }

        RoutesRenderer.displayLoading();
        RoutesMapDrawer.clearRouteLine();
        drawFullRoute(originCoords, destCoords, token);
    }

    async function drawFullRoute(fromCoords, toCoords, token) {
        // Busca rota via OSRM
        const routeData = await ApiClient.fetchRouteOSRM(fromCoords[0], fromCoords[1], toCoords[0], toCoords[1]);

        // Se entretanto foi pedida uma nova rota, ignorar este resultado
        if (token !== drawToken) return;

        // Desenha linha da rota
        if (routeData) RoutesMapDrawer.drawRouteLine(routeData.coordinates, MapModule.getMap());

        if (routeData && routeData.coordinates.length > 0) {

            let midpointCoords;
            if (routeData.coordinates.length > 0) midpointCoords = routeData.coordinates[Math.floor(routeData.coordinates.length / 2)];
            else midpointCoords = L.latLng((fromCoords[0] + toCoords[0]) / 2, (fromCoords[1] + toCoords[1]) / 2);

            let labelText = `${routeData?.distance || Utils.calculateDistance(fromCoords[0], fromCoords[1], toCoords[0], toCoords[1]).toFixed(1)}`;

            RoutesMapDrawer.drawLabel(midpointCoords, labelText, MapModule.getMap());
            RoutesMapDrawer.fitBoundsToRoute();

            // Renderiza instruções
            RoutesRenderer.displayRoute(routeData);
        }
    }

    function setRouteVisible(visible) {
        RoutesMapDrawer.setLineVisible(visible);
        RoutesMapDrawer.setMarkersVisible(visible);
    }

    return {
        updateAndDraw,
        init,
        getOrigin,
        getDestination,
        setOriginFromCoords,
        setDestinationFromCoords,
        setOriginFromPonto,
        setDestinationFromPonto,
        swapOriginDestination,
        useCurrentLocation,
        clear,
        setRouteVisible,
        setRouteLabelVisible
    };
})();