const RoutesMapDrawer = (function () {
    let routeLine = null;
    let routeMarkers = [];
    let routeLabel = null;
    let stepHighlight = null;
    let originMarker = null;
    let destinationMarker = null;

    function clearAll() {
        routeMarkers.forEach(marker => {
            try { MapModule.getMarkersLayerGroup().removeLayer(marker); }
            catch (e) { console.warn('Erro ao remover marcador:', e); }
        });

        routeMarkers = [];
        originMarker = null;
        destinationMarker = null;

    }

    function clearRouteLine() {
        const map = MapModule.getMap();

        if (routeLine) {
            map.removeLayer(routeLine);
            routeLine = null;
        }

        if (stepHighlight) {
            map.removeLayer(stepHighlight);
            stepHighlight = null;
        }

        if (routeLabel) {
            try { map.removeLayer(routeLabel); }
            catch (e) { }

            routeLabel = null;
        }
    }

    function drawMarker(coords, type, name) {
        const markersLayerGroup = MapModule.getMarkersLayerGroup();
        if (!markersLayerGroup) {
            console.error('markersLayerGroup não inicializado!');
            return;
        }

        const colors = type === 'origin' ? Constants.COLORS.origin : Constants.COLORS.destination;
        const label = type === 'origin' ? 'Origem' : 'Destino';
        const markerClass = type === 'origin' ? 'origin-circle' : 'destination-circle';

        // Remover o marcador anterior do mesmo tipo
        if (type === 'origin' && originMarker) {
            try {
                markersLayerGroup.removeLayer(originMarker);
                const idx = routeMarkers.indexOf(originMarker);
                if (idx > -1) routeMarkers.splice(idx, 1);
            } catch (e) { console.warn('Erro ao remover marcador anterior:', e); }
        }
        else if (type === 'destination' && destinationMarker) {
            try {
                markersLayerGroup.removeLayer(destinationMarker);
                const idx = routeMarkers.indexOf(destinationMarker);
                if (idx > -1) routeMarkers.splice(idx, 1);
            } catch (e) { console.warn('Erro ao remover marcador anterior:', e); }
        }

        // Criar novo marcador
        try {
            const marker = L.circleMarker(coords, {
                radius: 8,
                fillColor: colors.fill,
                color: colors.stroke,
                weight: 3,
                opacity: 0.9,
                fillOpacity: 0.8,
                className: `route-marker ${markerClass}`
            }).addTo(markersLayerGroup);

            marker.bindPopup(`<div class="ponto-popup"><strong>${label}: ${name}</strong></div>`);

            // Adicionar classes ao elemento SVG do Leaflet
            const svgElement = marker._path || marker._container;
            
            if (svgElement) {
                svgElement.classList.add(markerClass);
                svgElement.classList.add('route-marker');
            }

            routeMarkers.push(marker);

            // Guardar referência ao marcador para remoção posterior
            if (type === 'origin') originMarker = marker;
            else destinationMarker = marker;

            MapModule.getMap().setView(coords, 13);
        } catch (e) { console.error(`Erro ao criar marcador ${type}:`, e); }
    }

    function drawRouteLine(coordinates, map) {
        routeLine = L.polyline(coordinates, {
            color: Constants.COLORS.origin.fill,
            weight: 4,
            dashArray: '10, 8',
            className: 'route-polyline'
        }).addTo(map);    }

    function drawLabel(coords, labelText, map) {
        if (routeLabel) {
            try { map.removeLayer(routeLabel); } catch (e) { }
        }

        routeLabel = L.marker(coords, {
            icon: L.divIcon({
                className: 'route-label-icon',
                html: `<div class="route-label-box">${labelText}</div>`,
                iconSize: null,
                iconAnchor: [null, null]
            })
        }).addTo(map);
    }

    function highlightSegment(coordinates) {
        const map = MapModule.getMap();

        if (stepHighlight) map.removeLayer(stepHighlight);

        stepHighlight = L.polyline(coordinates, {
            color: Constants.COLORS.highlight.fill,
            weight: 6,
            dashArray: '10, 8',
            className: 'route-polyline'
        }).addTo(map);
    }

    function clearHighlight() {
        const map = MapModule.getMap();
        if (stepHighlight) {
            map.removeLayer(stepHighlight);
            stepHighlight = null;
        }
    }

    function setLineVisible(visible) {
        const map = MapModule.getMap();
        if (routeLine) {
            if (visible) map.addLayer(routeLine);
            else map.removeLayer(routeLine);
        }
    }

    function setMarkersVisible(visible) {
        const markersLayerGroup = MapModule.getMarkersLayerGroup();
        routeMarkers.forEach(m => {
            try {
                if (visible) markersLayerGroup.addLayer(m);
                else markersLayerGroup.removeLayer(m);
            } catch (e) { }
        });
    }

    function setLabelVisible(visible) {
        if (!routeLabel) return;
        const map = MapModule.getMap();
        try {
            if (visible) map.addLayer(routeLabel);
            else map.removeLayer(routeLabel);
        } catch (e) { }
    }

    function fitBoundsToRoute() { if (routeLine) MapModule.getMap().fitBounds(routeLine.getBounds(), { padding: [50, 50], maxZoom: 16 }); }

    return {
        clearAll,
        clearRouteLine,
        drawMarker,
        drawRouteLine,
        drawLabel,
        highlightSegment,
        clearHighlight,
        setLineVisible,
        setMarkersVisible,
        setLabelVisible,
        fitBoundsToRoute
    };
})();
