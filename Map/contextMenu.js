const ContextMenuModule = (function () {
    let el = null;
    let coords = null;
    let menuItems = {};
    let timer = null;

    function init() {
        el = document.getElementById('context-menu');
        const targetElement = MapModule.getMap();

        targetElement.on('contextmenu', (e) => { open(e); });

        if (!'oncontextmenu' in document.documentElement) {
            targetElement.addEventListener('touchstart', (e) => { timer = setTimeout(() => { open(e); }, 800); });
            targetElement.addEventListener('touchend', () => { clearTimeout(timer); });
            targetElement.addEventListener('touchmove', () => { clearTimeout(timer); });
        }

        document.addEventListener('click', hide);

        menuItems = { 'mark': onMark, 'details': onDetails, 'nearby': onNearby, 'origin': onOrigin, 'destination': onDestination };
        for (const [key, method] of Object.entries(menuItems)) {
            const item = document.getElementById(`ctx-${key}`);
            if (item) item.addEventListener('click', method);
        }
    }

    function open(e) {
        e.originalEvent.preventDefault();
        show(e.originalEvent.clientX, e.originalEvent.clientY, e.latlng);
    }

    function onMark() {
        if (!coords) return;
        const ponto = PontosManager.createPonto({
            lat: coords.lat,
            lng: coords.lng,
            nome: prompt('Nome do ponto:', 'Novo Ponto').trim() || 'Novo Ponto',
            source: 'manual'
        });
        if (ponto) {
            PontosManager.addPonto(ponto);
            PontosManager.renderMarker(ponto, MapModule.getMarkersLayerGroup());
            PontosManager.saveManual();
            PointsListModule.renderPointsList();
        }
        hide();
    }

    function onDetails() {
        if (!coords) return;
        const savedCoords = { ...coords };
        hide();
        DetalhesModule.abrir({
            lat: savedCoords.lat,
            lng: savedCoords.lng,
            name: `${savedCoords.lat.toFixed(4)}, ${savedCoords.lng.toFixed(4)}`,
            display_name: `${savedCoords.lat.toFixed(4)}, ${savedCoords.lng.toFixed(4)}`
        });
    }

    function onNearby() {
        if (!coords) return;
        NearbyPointsModule.abrir(coords.lat, coords.lng);
        hide();
    }

    function onOrigin() {
        if (!coords) return;
        RoutesModule.setOriginFromCoords(coords.lat, coords.lng);
        hide();
    }

    function onDestination() {
        if (!coords) return;
        RoutesModule.setDestinationFromCoords(coords.lat, coords.lng);
        hide();
    }

    function show(x, y, latlng) {
        if (!latlng) return;

        const bounds = ModoBreno.isActive() ? ModoBreno.getBoundsLeaflet() : MapModule.getPortugalBoundsLeaflet();

        if (bounds.isValid() && !bounds.contains(latlng)) {
            alert(`Ops! Este local parece estar fora de ${ModoBreno.isActive() ? "Lisboa" : "Portugal"}. Tente clicar dentro do território para acessar as opções.`);
            return;
        }

        coords = latlng;
        el.style.left = x + 'px';
        el.style.top = y + 'px';

        // Adiciona classes de acordo com a metade do ecrã o clique ocorreu
        el.classList.toggle('reverse-x', x > window.innerWidth / 2);
        el.classList.toggle('reverse-y', y > window.innerHeight / 2);

        el.classList.add('active');
    }

    function hide() {
        el?.classList.remove('active');
        coords = null;
        clearTimeout(timer);
    }

    function getCoords() { return coords; }

    return {
        init,
        show,
        hide,
        getCoords
    };
})();
