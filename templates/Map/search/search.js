const SearchModule = (function () {
    let searchInput = null;

    function init() {
        searchInput = document.getElementById('search-input');

        if (!searchInput) {
            console.warn('SearchModule: Input de busca não encontrado');
            return;
        }

        SearchSuggestions.init();
        SearchResults.init();
        populateTypeFilter();

        searchInput.addEventListener('input', onSearchInput);
        searchInput.addEventListener('keydown', onKeyDown);
        document.addEventListener('click', onDocumentClick);

        document.getElementById('search-submit-btn').addEventListener('click', performSearch);
    }

    function populateTypeFilter() {
        const filterSelect = document.getElementById('search-type-filter');
        if (!filterSelect) return;

        filterSelect.innerHTML = '';
        for (const key in Constants.TIPOS) {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = Constants.TIPOS[key];
            filterSelect.appendChild(option);
        }
    }

    function performSearch() {
        const termo = searchInput.value.trim();
        if (!termo) return;

        SearchSuggestions.hide();

        // 1) Pesquisa local nos pontos de recolha (vindos da BD via API/snapshot)
        try {
            const pontos = RecolhaManager?.getPontos?.() || [];
            const q = termo.toLowerCase();
            const matches = (pontos || [])
                .filter(p => (p?.nome || '').toLowerCase().includes(q))
                .slice(0, 30)
                .map(p => ({
                    ...p,
                    _kind: 'recolha',
                    name: p.nome,
                    tipo: 'recolha',
                    tipo_traduzido: 'Ponto de recolha'
                }));

            if (matches.length > 0) {
                SearchResults.display(matches);
                return;
            }
        } catch (e) {
            console.warn('[SearchModule] Falha na pesquisa local de pontos:', e);
        }

        // 2) Pesquisa de lugares (Nominatim) como fallback
        ApiClient.searchNominatim(termo, { type: document.getElementById('search-type-filter')?.value || '', limit: 15 })
            .then(results => { displaySearchResults(results); })
            .catch(err => {
                console.error('Erro na busca:', err);
                SearchResults.displayNoResults();
            });
    }

    function displaySearchResults(results) {
        if (!results || results.length === 0) {
            SearchResults.displayNoResults();
            return;
        }

        PontosManager.clearSource('search');
        MapModule.getGeoJsonLayerGroup().clearLayers();

        results.forEach(resultado => {
            const ponto = PontosManager.createPonto({
                id: `search_${resultado.osm_id || Date.now()}_${Math.random()}`,
                lat: resultado.lat,
                lng: resultado.lng,
                nome: resultado.name,
                source: 'search'
            });

            if (ponto) {
                PontosManager.addPonto(ponto);
                PontosManager.setPontoRichData(ponto.id, resultado);
                PontosManager.renderMarker(ponto, MapModule.getMarkersLayerGroup());
                resultado._pontoId = ponto.id;
            }
        });

        SearchResults.display(results);
    }

    function onSearchInput(e) { SearchSuggestions.fetchWithDebounce(e.target.value.trim(), document.getElementById('search-type-filter')?.value || ''); }
    function onKeyDown(e) { SearchSuggestions.handleKeyDown(e, performSearch); }
    function onDocumentClick(e) { SearchSuggestions.hideOnClickOutside(e); }
    function search(query, options = {}) { return ApiClient.searchNominatim(query, options); }
    function reverse(lat, lng) { return ApiClient.reverseGeocode(lat, lng); }

    return {
        init,
        performSearch,
        displaySearchResults,
        search,
        reverse
    };
})();