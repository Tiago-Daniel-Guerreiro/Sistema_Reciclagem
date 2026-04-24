const SidebarModule = (function () {
    function localizarMe(el) {
        if (!navigator.geolocation) {
            alert('Geolocalização não suportada');
            return Promise.reject('Geolocalização não suportada');
        }

        if (!el) {
            console.error('Botão não encontrado');
            return Promise.reject('Botão não encontrado');
        }

        const textContent = el.textContent;
        el.disabled = true;
        el.textContent = 'Localizando...';

        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const { latitude: lat, longitude: lng } = position.coords;
                    MapModule.setCurrentLocation(lat, lng);
                    try { document.getElementById('sidebar').hidePopover(); } catch (e) { }
                    MapModule.getMap().setView([lat, lng], 13);
                    PontosManager.clearSource('location');

                    const locPonto = PontosManager.createPonto({
                        lat, lng,
                        nome: 'Minha Localização',
                        source: 'location'
                    });

                    if (locPonto) {
                        PontosManager.addPonto(locPonto);
                        PontosManager.renderMarker(locPonto, MapModule.getMarkersLayerGroup());
                        locPonto.marker.openPopup();
                    }
                    el.textContent = textContent;
                    el.disabled = false;
                    resolve(true);
                },
                (error) => {
                    console.error('Erro ao obter localização:', error);
                    el.textContent = textContent;
                    el.disabled = false;
                    reject(error);
                }
            );
        });
    }

    function setVariable(e) {
        if (e.checked) document.documentElement.style.removeProperty(`--${e.dataset.cssVar}`);
        else document.documentElement.style.setProperty(`--${e.dataset.cssVar}`, 'none');
    }

    function init() {
        const locateBtn = document.getElementById('locate-me-btn');
        const tabPontos = document.getElementById('tab-pontos');

        if (locateBtn) locateBtn.addEventListener('click', (ev) => { localizarMe(ev.target); });
        if (tabPontos) tabPontos.addEventListener('change', () => { PointsListModule.renderPointsList(); });

        document.querySelectorAll('[data-css-var]').forEach(e => {
            e.addEventListener('change', () => setVariable(e));
            setVariable(e);
        });
    }

    return { init, localizarMe };
})();
