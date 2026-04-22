const SearchResults = (function () {
    let resultsContainer = null;

    function init() {
        resultsContainer = document.getElementById('results');

        if (resultsContainer) {
            ModalRenderer.delegateEvents(resultsContainer, '.btn-details-search', handleDetailsClick);
            ModalRenderer.delegateEvents(resultsContainer, '.btn-show-search', handleShowMapClick);
        }
    }

    function display(results) {
        if (!resultsContainer) return;

        resultsContainer.innerHTML = '';

        if (!results || results.length === 0) {
            displayNoResults();
            return;
        }

        results.forEach(resultado => {
            const li = document.createElement('li');
            li.className = 'result-item';
            li.dataset.result = JSON.stringify(resultado);
            li.appendChild(createResultElement(resultado));
            resultsContainer.appendChild(li);
        });
    }

    function createResultElement(resultado) {
        const contentDiv = Utils.createElement('div', 'result-content');
        contentDiv.appendChild(Utils.createElement('div', 'result-name', Utils.escapeHtml(resultado.name)));

        // Mostrar tipo sempre que disponível
        const tipoText = resultado.tipo_traduzido || resultado.tipo || '';
        if (tipoText && tipoText.trim()) {
            const typeBadge = Utils.createElement('span', 'type-badge', Utils.escapeHtml(tipoText));
            contentDiv.appendChild(typeBadge);
        }

        const buttonsDiv = Utils.createElement('div', 'result-buttons');
        buttonsDiv.appendChild(createButton('btn-show-search', 'Mostrar'));
        buttonsDiv.appendChild(createButton('btn-details-search', 'Detalhes'));
        contentDiv.appendChild(buttonsDiv);

        return contentDiv;
    }

    function createButton(className, text) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = className;
        btn.textContent = text;
        return btn;
    }

    function handleShowMapClick(target) {
        try { focusOnMap(JSON.parse(target.closest('.result-item').dataset.result)); }
        catch (e) { console.error('Erro ao processar resultado:', e); }
    }

    function handleDetailsClick(target) {
        try { openDetails(JSON.parse(target.closest('.result-item').dataset.result)); }
        catch (e) { console.error('Erro ao processar resultado:', e); }
    }

    function focusOnMap(resultado) {
        if (!MapModule?.getMap) return;

        MapModule.getMap().setView([resultado.lat, resultado.lng], 14);

        if (resultado.polygon_geojson) MapModule.showArea?.(resultado);

        if (resultado?._kind === 'recolha') {
            try { RecolhaMarker?.focus?.(resultado, 16); } catch (e) { /* noop */ }
        }
    }

    function openDetails(resultado) {
        if (!DetalhesModule?.abrir) return;

        if (resultado?._kind === 'recolha') {
            DetalhesModule.abrir(resultado);
            return;
        }
        DetalhesModule.abrir(resultado);
    }

    function displayNoResults() {
        if (!resultsContainer) return;

        resultsContainer.innerHTML = '';
        resultsContainer.appendChild(Utils.createElement('div', 'result-no-items', 'Nenhum resultado encontrado.'));
    }

    return {
        init,
        display,
        createResultElement,
        handleShowMapClick,
        handleDetailsClick,
        focusOnMap,
        openDetails,
        displayNoResults
    };
})();
